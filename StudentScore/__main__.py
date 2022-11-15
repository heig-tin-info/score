#!/usr/bin/env python
import click

from .score import Score


@click.command()
@click.argument('file', type=click.File('r'), default='criteria.yml')
@click.option('--verbose', '-v', is_flag=True)
def cli(file=None, verbose=False):
    """Student Score. """
    score = Score(file)
    if verbose:
        print((f'Got {score.got:g} points + {score.bonus:g} '
               f'points out of {score.total:g} points'))

    click.secho(f'{score.mark:.1f}', fg="green" if score.success else "red")


if __name__ == '__main__':
    cli()
