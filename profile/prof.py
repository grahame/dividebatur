#1/usr/bin/env python3

if __name__ == '__main__':
    from dividebatur import senatecount
    import cProfile
    import sys
    cProfile.run('senatecount.main(*sys.argv[2:])', filename=sys.argv[1])
