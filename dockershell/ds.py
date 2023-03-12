import click
import logging
import textwrap

from rich.traceback import install

install()

@click.command
@click.option('-v','--verbose', count=True, help='Increase verbosity')
@click.option('-q','--quiet', count=True, help='Decrease verbosity')
@click.option('--init/--no-init', help='Generate an initial Dockerfile in the build root.')
@click.argument('command', nargs=-1)
def cli(verbose, quiet, init, command):
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
    log.debug(textwrap.dedent(f'''
    Settings:

      logging level ... {logging_level}
      init ............ {'yes' if init else 'no'}
      command ......... {command}
      '''))
