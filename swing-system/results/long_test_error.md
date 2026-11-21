# Long test failed (attempt 2)

```
Traceback (most recent call last):
  File "/home/runner/work/shri-labh-jewellers/shri-labh-jewellers/swing-system/scripts/run_longtest.py", line 16, in <module>
    longtest.run(send=True)
  File "/home/runner/work/shri-labh-jewellers/shri-labh-jewellers/swing-system/swing/longtest.py", line 470, in run
    O = nifty_test()
        ^^^^^^^^^^^^
  File "/home/runner/work/shri-labh-jewellers/shri-labh-jewellers/swing-system/swing/longtest.py", line 344, in nifty_test
    hi, lo, dopen = h[first].max(), l[first].min(), o[0]
                    ^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/numpy/_core/_methods.py", line 41, in _amax
    return umr_maximum(a, axis, None, out, keepdims, initial, where)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: zero-size array to reduction operation maximum which has no identity

```
