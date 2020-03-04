from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def add_series(T1, V1, T2, V2, zl=True, zr=False, verbose=False):

    T1 = T1.copy(); V1 = V1.copy()
    T2 = T2.copy(); V2 = V2.copy()
    TS = [];        VS = []
    i1 = 0;         i2 = 0

    if T1 != sorted(T1): print("[ERROR] first time series not sorted")
    if T2 != sorted(T2): print("[ERROR] second time series not sorted")

    T1min = T1[0]; T1max = T1[-1]
    T2min = T2[0]; T2max = T2[-1]
    TSmin = min(T1min, T2min)
    TSmax = max(T1max, T2max)

    if T1min != T2min and verbose: print("[WARN] time series do not share same start date (%s, %s)" % (T1min, T2min))
    if T1max != T2max and verbose: print("[WARN] time series do not share same end date (%s, %s)" % (T1max, T2max))

    if T1min > T2min:
        T1.insert(0, T2min)
        if zl: val = 0.
        else:  val = V1[0]
        V1.insert(0, val)
        if verbose: print("[WARN] expanding first time series to left with value of %.2f" % val)
    elif T2min > T1min:
        T2.insert(0, T1min)
        if zl: val = 0.
        else:  val = V2[0]
        V2.insert(0, val)
        if verbose: print("[WARN] expanding second time series to left with value of %.2f" % val)

    if T1max < T2max:
        T1.append(T2max)
        if zr: val = 0.
        else:  val = V1[-1]
        V1.append(val)
        if verbose: print("[WARN] expanding first time series to right with value of %.2f" % val)
    elif T2max < T1max:
        T2.append(T1max)
        if zr: val = 0.
        else:  val = V2[-1]
        V2.append(val)
        if verbose: print("[WARN] expanding second time series to right with value of %.2f" % val)

    while True:
        try:
            if T1[i1] == T2[i2]:
                TS.append(T1[i1])
                VS.append(V1[i1] + V2[i2])
                i1 += 1
                i2 += 1
            elif T1[i1] < T2[i2]:
                TS.append(T1[i1])
                VS.append(V1[i1] + V2[i2-1])
                i1 += 1
            elif T1[i1] > T2[i2]:
                TS.append(T2[i2])
                VS.append(V1[i1-1] + V2[i2])
                i2 += 1
        except IndexError:
            break

    return TS, VS

dts = datetime(2019,  1,  1)

T1 = [dts + timedelta(days=x) for x in range(0, 10)]
V1 = [(d-dts).days for d in T1]

T2 = [dts + timedelta(days=2*x) for x in range(1, 10)]
V2 = [(d-dts).days+5 for d in T2]

TS, VS = add_series(T1, V1, T2, V2)

plt.step(T1, V1, where="post")
plt.step(T2, V2, where="post")
plt.step(TS, VS, where="post")
plt.show()
