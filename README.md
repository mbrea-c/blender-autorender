## Running

I used nix to package this project, since there's a non-trivial amount of system
dependencies that cannot be captured by Poetry. So, if you haven't already, [set
up nix](https://nixos.org/download/)! Make sure you also enable nix command and
flakes experimental features ([instructions](https://nixos.wiki/wiki/flakes)).

Once you have that, you can:
* Run the program with
  ```bash
  nix run . PROGRAM_ARGS
  ```
  where in this case, `PROGRAM_ARGS` is just the path to the `.json` sprite
  render config.
* Enter into a shell environment where all the dependencies are available and in
  your path, plus you have the Poetry CLI available. Good for starting your
  editor from there, so that Pyright has access to all python modules without
  weird config tricks. To do this, run

  ```bash
  nix develop
  ```

  Direnv will do this automatically for you if you have it configured to do so.

Alternatively, the boring way is to just look at the `flake.nix` file, install
the system dependencies manually (e.g. `apt install <stuff>` if you're on
Ubuntu) and run the program with Poetry.
