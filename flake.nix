{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    let
      lib = nixpkgs.lib;
      forSystems =
        systems: forSystem: builtins.foldl' lib.attrsets.recursiveUpdate { } (map forSystem systems);
      forAllSystems = forSystems [
        "x86_64-linux"
        "x86_64-darwin"
        "aarch64-linux"
        "aarch64-darwin"
      ];
    in
    forAllSystems (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
        overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

        # bpy needs additional native dependencies
        bpyOverlay = final: prev: {
          bpy = prev.bpy.overrideAttrs (old: {
            # Without this, missing cuda libs trigger build failure
            autoPatchelfIgnoreMissingDeps = true;
            propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
              pkgs.pkg-config # used by bpy’s build scripts
              pkgs.xorg.libX11 # libX11.so.6 :contentReference[oaicite:2]{index=2}
              pkgs.xorg.libXrender # libXrender.so.1
              pkgs.xorg.libXfixes # libXfixes.so.3
              pkgs.xorg.libXi # libXi.so.6
              pkgs.xorg.libXt
              pkgs.xorg.libSM # libSM.so.6
              pkgs.xorg.libXxf86vm # libXxf86vm.so.1
              pkgs.libxkbcommon
            ];
            buildInputs = (old.buildInputs or [ ]) ++ [
              pkgs.rocmPackages.clr
              pkgs.level-zero
              # CUDA has an unfree license. I don't need it, so I'll keep it
              # disabled
              # cudaPackages.cudatoolkit
            ];
          });

        };

        pythonBase = pkgs.callPackage pyproject-nix.build.packages { inherit python; };
        pythonSet = pythonBase.overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
            bpyOverlay
          ]
        );
        inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;

        appVirtualEnv = pythonSet.mkVirtualEnv (
          pythonSet.blender-autorender.pname + "-env"
        ) workspace.deps.default;

        blender-autorender-package = mkApplication {
          venv = appVirtualEnv;
          package = pythonSet.blender-autorender;
        };
      in
      {
        packages."${system}" = rec {
          default = blender-autorender;
          blender-autorender = blender-autorender-package;
        };
      }
    );
}
