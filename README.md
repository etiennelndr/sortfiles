Sort files
==========

A simple way to sort pictures and videos of a folder by year and month.

Installation
------------

Python 3.14 and [Poetry](https://python-poetry.org/) are required:

```
poetry install
```

Getting started
---------------

### Sort files

Given a directory which contains files and/or directories, you can sort all the files 
with the following command:

```
sortfiles sort <directory>
```

Each supported file is moved to a `<year>/<month>` folder created in `<directory>`. Its path 
relative to `<directory>` is kept:

```
<directory>                     <directory>
├── IMG_0001.jpg                └── 2024
└── holidays            =>          ├── 05
    └── IMG_0002.jpg                │   └── IMG_0001.jpg
                                    └── 10
                                        └── holidays
                                            └── IMG_0002.jpg
```

The date of a picture is read from its EXIF metadata (shooting date). If it is missing, and for
videos, the oldest date between the creation and the modification of the file is used.

Sidecars (e.g. `IMG_0001.aae` or `IMG_0001.jpg.xmp`) are moved along with the picture or the video
of the same name.

Files which are already located in a `<year>/<month>` folder and unsupported files are left
untouched.

| Option            | Description                                                |
|-------------------|------------------------------------------------------------|
| `-c`, `--clean`   | Delete the old subfolders left empty after moving files    |
| `-d`, `--dry-run` | Only log what would be moved, without modifying any file   |
| `-v`, `--verbose` | Increase logging verbosity                                 |

### Merge duplicate pictures

Some devices keep both the original picture (`IMG_1234.jpg`) and its edited version
(`IMG_E1234.jpg`). The following command replaces each original HEIC or JPEG picture with its
edited version:

```
sortfiles merge <directory>
```

`<directory>` is processed recursively. The merged picture keeps the name of the original one and
the extension of the edited one: `IMG_1234.heic` and `IMG_E1234.jpg` are merged into `IMG_1234.jpg`.

| Option            | Description                                                |
|-------------------|------------------------------------------------------------|
| `-d`, `--dry-run` | Only log what would be merged, without modifying any file  |
| `-v`, `--verbose` | Increase logging verbosity                                 |

Supported files
---------------

- Pictures: HEIC, JPEG, PNG and raw formats (ARW, CR2, DNG, NEF, RAW)
- Videos: MOV and MP4
- Sidecars: AAE and XMP