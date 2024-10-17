{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, poetry2nix }:
    let
      supportedSystems =
        [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
      deps = pkgs: with pkgs; [ xorg.libXxf86vm xorg.libXfixes ];
      myOverrides = pkgs: final: prev: {
        bpy = prev.bpy.overridePythonAttrs (old: {
          autoPatchelfIgnoreMissingDeps = true;
          nativeBuildInputs = old.nativeBuildInputs or [ ]
            ++ [ pkgs.pkg-config ];
          buildInputs = old.buildInputs or [ ] ++ (with pkgs; [
            xorg.libXxf86vm
            xorg.libXfixes
            xorg.libXi
            libxkbcommon
            xorg.libXt
            rocmPackages.clr
            # CUDA has an unfree license. I don't need it, so I'll keep it
            # disabled
            # cudaPackages.cudatoolkit
            level-zero
          ]);
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
            python = pkgs.${system}.python311;
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
                  python = python311;
                  overrides =
                    overrides.withDefaults (myOverrides pkgs.${system});
                })
                poetry
              ] ++ deps pkgs.${system};
          };
        });
    };
}
