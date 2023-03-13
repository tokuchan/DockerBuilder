import click
import logging
import textwrap

from io import StringIO
from pathlib import Path
from rich.traceback import install
from sh import git

install()

gitRoot= getattr(git, 'rev-parse').bake(show_toplevel=True)

def getRoot():
    '''
    Discover the root of the build. Look in each directory between here and
    project root for a Dockerfile. If one is found, then that is the build
    root.
    '''
    log= logging.getLogger('cli.root')
    git_root= Path(gitRoot().strip()).resolve()
    for parent in (Path().cwd()/Path('foo')).parents:
        log.debug(f'Trying: {parent}')
        if (parent / Path('Dockerfile')).exists():
            log.debug(f'Found root: {parent}')
            return parent.resolve()
        if parent == git_root:
            return git_root
    return git_root

@click.command
@click.option('-n/-N','--dry-run/--no-dry-run',help='If set, do not actually do anything.')
@click.option('-v','--verbose', count=True, help='Increase verbosity.')
@click.option('-q','--quiet', count=True, help='Decrease verbosity.')
@click.option('--init/--no-init', help='Generate an initial Dockerfile in the build root.')
@click.option('--dockerfile', help='Specify a dockerfile, otherwise we guess at one.')
@click.option('--dsrc', help='Specify a ds.rc command file, otherwise we guess at one.')
@click.argument('command', nargs=-1)
def cli(dry_run, verbose, quiet, init, command, dockerfile=None, dsrc=None):
    '''
    Using Docker, run the given command within a custom build image.

    The command first determines a "build root", which is the directory at or
    above the CWD that contains the project's .git directory. Then, if
    necessary, it creates a Dockerfile at that location (you should consider
    tracking this file as your project's build environment). Next, ds runs
    Docker, using that Dockerfile, setting a shell as entrypoint and running
    the supplied command.
    '''
    logging_level= logging.WARN - 10*verbose + 10*quiet
    logging.basicConfig(level=logging_level)
    log= logging.getLogger('cli')

    log.info('Starting')
    command= ' '.join(command)
    root= getRoot()
    dockerfile_path= Path(dockerfile).resolve() if dockerfile else root/Path('Dockerfile')
    dsrc_path= Path(dsrc).resolve() if dsrc else root/Path('ds.rc')
    log.debug(textwrap.dedent(f'''
    Settings:

      logging level ..... {logging_level}
      init .............. {'yes' if init else 'no'}
      command ........... {command}
      root .............. {root}
      Dockerfile path ... {dockerfile_path} {'[EXISTS]' if dockerfile_path.exists() else '[ABSENT]'}
      ds.rc path ........ {dsrc_path} {'[EXISTS]' if dsrc_path.exists() else '[ABSENT]'}
      '''))


