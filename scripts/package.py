"""Create a clean AppSail build directory and an optional deployment ZIP."""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ['app.py', 'gunicorn.conf.py', 'requirements.txt', 'sample_test_input.csv']
DIRECTORIES = ['energy', 'static', 'models']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-deps', action='store_true', help='Vendor production dependencies from the Python package registry.')
    parser.add_argument('--zip', action='store_true', help='Create GridLens_AppSail.zip after preparing the build.')
    parser.add_argument('--source', action='store_true', help='Create the complete source archive, excluding secrets, environments and generated builds.')
    args = parser.parse_args()
    if args.zip and not args.install_deps:
        parser.error('Use --install-deps with --zip so the AppSail archive includes its web server.')
    if args.source:
        excluded={'.runtime','build','__pycache__','.venv','.venv-training','.git','.agents','.codex','.presentation-build','node_modules'}
        archive_path=ROOT/'GridLens_Source.zip'
        with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(ROOT.rglob('*')):
                relative=path.relative_to(ROOT)
                if not path.is_file() or any(part in excluded for part in relative.parts):continue
                if path.suffix in ('.zip','.pyc','.log') or path.name in ('.env','.catalystrc','.DS_Store'):continue
                if path.name.startswith('.env.') and path.name!='.env.example':continue
                archive.write(path,Path('gridlens')/relative)
        print('Created '+str(archive_path))
        if not args.zip and not args.install_deps:return
    output = ROOT / 'build'
    if output.is_symlink():
        raise SystemExit('Refusing to replace a symlink at build/.')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for filename in FILES:
        shutil.copy2(ROOT / filename, output / filename)
    for name in DIRECTORIES:
        shutil.copytree(ROOT / name, output / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if args.install_deps:
        # Universal wheels keep a build prepared on macOS portable to AppSail Linux.
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '--no-compile',
                        '--only-binary=:all:', '--platform', 'any', '--python-version', '3.12',
                        '-r', str(ROOT / 'requirements.txt'), '-t', str(output)], check=True)
    if args.zip:
        archive = shutil.make_archive(str(ROOT / 'GridLens_AppSail'), 'zip', output)
        print('Created ' + archive)
    print('Prepared ' + str(output))
    if not args.install_deps:
        print('Production dependencies are not installed. Run again with --install-deps before deployment.')


if __name__ == '__main__':
    main()
