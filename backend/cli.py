import argparse

from .store import Store


def main():
    parser = argparse.ArgumentParser(description='Private operations; never expose over HTTP')
    parser.add_argument('command', choices=['init', 'invite', 'maintain'])
    args = parser.parse_args()
    store = Store.configured()
    if args.command == 'invite':
        print(store.invite())  # Display once on a private, non-recorded admin terminal.
    elif args.command == 'init':
        store.init()
    else:
        store.maintain()


if __name__ == '__main__':
    main()
