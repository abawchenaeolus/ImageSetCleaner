import ast
import csv
import click
import os
import pathlib
import shutil
import subprocess


class PythonLiteralOption(click.Option):

    def type_cast_value(self, ctx, value):
        try:
            return ast.literal_eval(value)
        except:
            raise click.BadParameter(value)


def move_to_set(path):
    basename = os.path.basename(path)
    set_path = os.path.join(
        os.path.dirname(path), 'set-{}'.format(basename))
    pathlib.Path(set_path).mkdir(exist_ok=True)
    image_source_path = os.path.join(set_path, basename)
    shutil.rmtree(image_source_path, ignore_errors=True)
    shutil.copytree(path, image_source_path)
    return image_source_path


def load_files(path):
    # click.echo('load files from {}'.format(path))
    return set(os.listdir(path))


def execute(cmnd):
    click.echo(cmnd)
    pipes = subprocess.Popen(
        cmnd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        err_msg = "%s \n %s. \nCode: %s" % (cmnd, std_err.strip(), pipes.returncode)
        click.secho(err_msg, bg='blue', fg='white')


def copy_image(input, output):
    shutil.rmtree(output, ignore_errors=True)
    cmnd = ' '.join([
        'cp', '-r', input, output
    ])
    execute(cmnd)


def cal(image_dir, relocation_dir, method, pollution):
    cmnd = ' '.join([
        'python',
        'image_set_cleaner.py',
        '--processing=move',
        '--image_dir={}'.format(image_dir),
        '--relocation_dir={}'.format(relocation_dir),
        '--clustering_method={}'.format(method),
        '--pollution_percent={}'.format(pollution),
    ])
    execute(cmnd)


@click.group()
def cli():
    pass

# https://stackoverflow.com/a/47730333/9041712
@cli.command()
@click.argument('basepath', type=click.Path(exists=True))
@click.option('--methods', '-ms', cls=PythonLiteralOption, default=\
    "['kmeans', 'birch', 'gaussian_mixture', 'agglomerative_clustering']")
@click.option('--pollutions', default=range(41))
def detect(basepath, methods, pollutions):
    path = move_to_set(basepath)
    params = [(m, p) for m in methods for p in pollutions]
    for m, p in params:
        image_dir = '{}-{}-{}'.format(path, m, p)
        copy_image(path, image_dir)

        relocation_dir = '{}-outlier'.format(image_dir)
        shutil.rmtree(relocation_dir, ignore_errors=True)

        os.makedirs(relocation_dir)
        cal(image_dir, relocation_dir, m, p)


@cli.command()
@click.argument('source-path', type=click.Path(exists=True))
@click.argument('yes-path', type=click.Path(exists=True))
@click.argument('no-path', type=click.Path(exists=True))
@click.option('--methods', '-ms', default=[
    'kmeans', 'birch', 'gaussian_mixture', 'agglomerative_clustering'])
@click.option('--pollutions', default=range(41))
@click.option('--report-path', type=click.Path())
@click.option('--detail-path', type=click.Path())
def evaluate(
    source_path, yes_path, no_path, methods, pollutions, report_path, detail_path):
    workspace = os.path.dirname(source_path)
    actual_yes = load_files(yes_path)
    actual_no = load_files(no_path)

    report_path = report_path or os.path.join(workspace, 'report.csv')
    report_out = open(report_path, 'w')
    report_writer = csv.writer(report_out)
    report_writer.writerow(['method', 'pollution', 'TN', 'FP', 'FN', 'TP'])

    detail_path = detail_path or os.path.join(workspace, 'detail.csv')
    detail_out = open(detail_path, 'w')
    detail_writer = csv.writer(detail_out)
    detail_writer.writerow(['method', 'pollution', 'filename'])

    for m, p in [(m, p) for m in methods for p in pollutions]:
        predict_yes_path = '{}-{}-{}'.format(source_path, m, p)
        predict_no_path = '{}-outlier'.format(predict_yes_path)
        predict_yes = load_files(predict_yes_path)
        predict_no = load_files(predict_no_path)
        # http://www.dataschool.io/simple-guide-to-confusion-matrix-terminology/
        tn = actual_no.intersection(predict_no)
        fp = actual_no.intersection(predict_yes)
        fn = actual_yes.intersection(predict_no)
        tp = actual_yes.intersection(predict_yes)
        report_writer.writerow([m, p, len(tn), len(fp), len(fn), len(tp)])
        detail_writer.writerows(([m, p, filename] for filename in fp))

    report_out.close()

if __name__  == '__main__':
    cli()
