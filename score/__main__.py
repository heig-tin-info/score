#!/usr/bin/env python3
import click

from .score import Score


@click.command()
@click.argument('file', type=click.File('r'), default='criteria.yml')
@click.option('--verbose', '-v', is_flag=True)
def cli(file, verbose):
    score = Score(file)
    if verbose:
        print(f'Got {score.got:g} points + {score.bonus:g} points out of {score.total:g} points')

    click.secho(f'{score.mark:g}', fg="green" if score.success else "red")


if __name__ == '__main__':
    cli()
