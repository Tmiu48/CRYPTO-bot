{
  description = "CRYPTO-bot nix development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: import nixpkgs { inherit system; };
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          pythonEnv = pkgs.python3.withPackages (ps: with ps; [
            streamlit
            pandas
            yfinance
            requests
            plotly
            numpy
            pip
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [ pythonEnv ];

            shellHook = ''
              export PIP_PREFIX=$(pwd)/.pip_packages

              export PYTHONPATH="$PIP_PREFIX/${pkgs.python3.sitePackages}:$PYTHONPATH"

              export PATH="$PIP_PREFIX/bin:$PATH"

              unset SOURCE_DATE_EPOCH

              pip install ccxt
            '';
          };
        }
      );
    };
}
