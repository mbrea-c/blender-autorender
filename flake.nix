{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, poetry2nix }:
    let
      python = pkgs: pkgs.python311;
      pythonPackages = pkgs: pkgs.python311Packages;

      supportedSystems =
        [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
      deps = pkgs:
        with pkgs; [
          xorg.libXxf86vm
          xorg.libXfixes
          xorg.libX11
          pkg-config
        ];

      myOverrides = pkgs: final: prev: {
        mypy-extensions = prev.mypy-extensions.overridePythonAttrs (oldAttrs: {
          nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ])
            ++ (with (pythonPackages pkgs); [ flit-core ]);
        });

        bpy = prev.bpy.overridePythonAttrs (old: {
          autoPatchelfIgnoreMissingDeps = true;
          propagatedBuildInputs = old.propagatedBuildInputs or [ ] ++ [
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
          buildInputs = old.buildInputs or [ ] ++ [
            pkgs.rocmPackages.clr
            pkgs.level-zero
            # CUDA has an unfree license. I don't need it, so I'll keep it
            # disabled
            # cudaPackages.cudatoolkit
          ];
        });
      };
    in {
      packages = forAllSystems (system:
        let
          inherit (poetry2nix.lib.mkPoetry2Nix { pkgs = pkgs.${system}; })
            mkPoetryApplication overrides;
        in {
          default = mkPoetryApplication {
            projectDir = self;
            python = python pkgs.${system};
            buildInputs = deps pkgs.${system};
            overrides = overrides.withDefaults (myOverrides pkgs.${system});
          };
        });

      devShells = forAllSystems (system:
        let
          inherit (poetry2nix.lib.mkPoetry2Nix { pkgs = pkgs.${system}; })
            mkPoetryEnv overrides;
        in {
          default = pkgs.${system}.mkShellNoCC {
            packages = with pkgs.${system};
              [
                (mkPoetryEnv {
                  projectDir = self;
                  python = python pkgs.${system};
                  overrides =
                    overrides.withDefaults (myOverrides pkgs.${system});
                })
                poetry
              ] ++ deps pkgs.${system};
          };
        });
    };
}
