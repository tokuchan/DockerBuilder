import click

from rich.traceback import install

install()

@click.command
def cli():
    '''
    Using Docker, run the given command within a custom build image.
    '''
    pass
