# PeridexisErrant's Starter Pack Manager

This project is NOT an actual pack, or intended for public use.
[See here](http://www.bay12forums.com/smf/index.php?topic=126076) for that.

There is *no support* for using this tool - it is designed for my own use,
and released in the hope that others might find it useful.
Bug reports are most welcome; feature requests are not
(missing OS support is considered a bug - it should work on Windows, OSX, and Linux).

**What it does:**

- Read a config file that describes the pack
- Check the latest version released on on DFFD or Github
- Download stuff if an update or missing file is detected
- Assemble it all in the correct directory structure
- Configure all the paths etc. that can be set automatically
- Create some components at runtime; eg ASCII graphics
- Zip up the built pack, ready to upload
- Generate or manage changelogs, contents list, and forum post

For anyone using these tools to assemble their own pack:

- Note that the license ([Affero GPL 3+](https://www.gnu.org/licenses/agpl))
  applies to all the code, and to the code *only*.

  Some files in `./base/` are mine; some are by other people in
  the Dwarf Fortress community.  Treat these files as if they are
  under an informal version of the [CC-BY-SA license](https://creativecommons.org/licenses/by-sa/4.0).

  Any outputs you produce with this software are entirely your
  own, subject to licenses of the components you downloaded.
  The pack I publish is shared under the informal system above.

- Check out `config.yml` and `components.yml`.  The system is
  set up and configured via these files, which are also commented.

- You will need Python 3.5+, as I make extensive use of several
  new features.  You will also need the `requests` and `pyaml`
  libraries (both can be installed with `pip`).

  Optional dependencies to unpack exotic archive types may be
  added in future, but will not be required.

- Many items in the provided config will only work on Windows
  (or when building for windows on another OS; tested on Debian).
  If you are interested in helping support OSX or Linux, please
  get in touch with my handle at gmail.
