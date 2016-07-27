from .senatecount import main as count_main
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_file',
        type=str,
        help='JSON config file for counts')
    parser.add_argument(
        'out_dir',
        type=str,
        help='Output directory')
    args = parser.parse_args()
    count_main(args.config_file, args.out_dir)
