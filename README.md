# pyWaveRecipe

This library contains tools for storing S-parameters from electromagnetic components and combine them while preserving external dependencies of each components.

## Component object

This object contains S-parameters and all properties related to an individual physical component.

To instantiate a new component, you must precise the number of ports.
```python
amplifier = Component(2)
```

S-parameters are stored using the Pandas python library in the ```SMatrices``` property of ```Component``` object. In 0.0.18 version of the pyWaveRecipe library, default column names are :
- Frequency (Hz)
- S{\d}{\d} (dB)

With **{\d}** representing a digit. A combination of two of them represent a classic S-parameter port index.

> **⚠️ Warning ⚠️**
>
> In case of wrong port index, it results in an error while using the ```Circuit``` object.

As a Pandas ```DataFrame``` object, ```SMatrices``` supports parametric S-parameters out of just frequency ones. If your physical component is dependent on temperature, you can add temperature specific S-parameters rows.

This object can be (re)stored as text through its methods : ```ToCSVStream```, ```ToCSVString```, ```FromCSVStream```, or ```FromCSVFile```.

## Circuit object

This object is used to build a combination of several ```Component```s and heritates from "networkx" ```Graph``` (i.e., have same properties, fields, and methods).

Each node corresponds to a ```Component```, and each edge corresponds to a connection between two ports of two ```Component```s.

When the complete physical circuit is represented as a graph, you can use the ```Synthesize``` method to get a single ```Component``` object. S-parameters heritate all dependencies that each ```Component```s have. Combining two ```Component```s where one has a dependency duplicates all S-parameters from the other to compute resulting combined S-parameters.

This behaviour is different for frequency-dependency. Only the common frequency rows are kept.