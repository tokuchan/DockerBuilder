import click
import logging
import os
import textwrap

from io import StringIO
from pathlib import Path
from rich.traceback import install
from sh import git, docker
from subprocess import Popen, PIPE, CalledProcessError

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

def createDockerfile( dockerfile_path:Path ):
    '''Create a new Dockerfile at the specified path.'''
    log= logging.getLogger('cli.createDockerfile')
    log.info('Creating Dockerfile file')
    dockerfile_path.unlink(missing_ok=True)
    with dockerfile_path.open('w') as fout:
        fout.write(textwrap.dedent('''            FROM ubuntu:latest AS base

            ARG user
            ARG uid
            
            # Keep apt tools from prompting
            ARG DEBIAN_FRONTEND=noninteractive
            ENV TZ=America/Ny
            
            # Inflate the system and set up APT.
            RUN yes | unminimize
            RUN apt-get -y install dialog apt-utils tzdata git
            RUN git clone https://github.com/timothyvanderaerden/add-apt-repository.git /usr/local/share/add-apt-repository
            RUN chmod ugo+rx /usr/local/share/add-apt-repository/add-apt-repository
            RUN ln -s /usr/local/share/add-apt-repository/add-apt-repository /usr/local/bin/add-apt-repository

            FROM base AS package-install
            
            # Install needed packages
            RUN apt-get update

            # Shells
            #RUN apt-get -y install bash
            RUN apt-get -y install fish
            #RUN apt-get -y install tcsh
            #RUN apt-get -y install zsh

            # System support
            RUN apt-get -y install locales
            RUN apt-get -y install man
            RUN apt-get -y install sshfs
            RUN apt-get -y install sudo
            RUN apt-get -y install stow
            RUN apt-get -y install unzip

            # Programming languages
            RUN apt-get -y install python3

            # Utilties
            RUN apt-get -y install bat
            RUN apt-get -y install curl
            RUN apt-get -y install exa
            RUN apt-get -y install jq
            RUN apt-get -y install ripgrep
            RUN apt-get -y install sqlite3
            RUN apt -y autoremove

            FROM package-install AS user-setup

            #RUN ln -s /home/${user}/host/home/${user}/.Xauthority /home/${user}/.Xauthority
            # Set up a user and switch to that user for the remaining commands
            RUN useradd -u ${uid} -ms /usr/bin/fish ${user}
            RUN adduser ${user} sudo
            RUN echo 'ALL            ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers

            # Set up environment
            ENV LANGUAGE="en_US.UTF-8"
            ENV LC_ALL="en_US.UTF-8"
            ENV LC_CTYPE="en_US.UTF-8"
            ENV LANG="en_US.UTF-8"
            RUN locale-gen en_US.UTF-8
            RUN dpkg-reconfigure locales
            ENV SSH_AUTH_SOCK=${SSH_AUTH_SOCK}

            FROM user-setup AS python-setup

            RUN mkdir -p /usr/local/share/python-pip
            RUN curl -Lo /usr/local/share/python-pip/get-pip.py https://bootstrap.pypa.io/get-pip.py
            RUN sudo python3 /usr/local/share/python-pip/get-pip.py

            RUN pip install --upgrade pip rich-cli termsql ipython

            FROM python-setup AS user-shell

            WORKDIR /work
            ENTRYPOINT ["/bin/bash"]
        '''))

def createDsrc(dsrc_path:Path):
    log= logging.getLogger('cli.createDsrc')
    log.info('Creating ds.rc file')
    dsrc_path.unlink(missing_ok=True)
    with dsrc_path.open('w') as fout:
        fout.write(textwrap.dedent(f'''bash
        '''))


def runCommand(cmd:str):
    '''Call cmd in the shell, logging output.'''
    log= logging.getLogger('cli.runCommand')

    with Popen(cmd, stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            log.info(line, end='') # process line here

    if p.returncode != 0:
        raise CalledProcessError(p.returncode, p.args)

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

    if init:
        if dry_run:
            log.info('Would have created docker file at: {dockerfile_path}')
        else:
            createDockerfile(dockerfile_path)

    if init: 
        if dry_run:
            log.info('Would have created dsrc file at: {dsrc_path}')
        else:
            createDsrc(dsrc_path)

    if dockerfile_path.exists():
        if dry_run:
            log.info('Would have built dockershell:latest')
            log.info('Would have run dockershell:latest')
        else:
            runCommand(['docker', 'buildx', 'build', '.', '-t', 'dockershell:latest', '--build-arg', 'user=seans', '--build-arg', 'uid=1000'])
            os.execlp('docker', 'docker', 'run', '-v', '.:/work', '-it', '--rm', '--entrypoint', '/usr/bin/fish', '--workdir', '/work', '-u', 'seans', 'dockershell:latest')
