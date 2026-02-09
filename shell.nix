{ pkgs ? import <nixpkgs> {} }:

let
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
pkgs.mkShell {
  buildInputs = [ pythonEnv ];

  shellHook = ''
    export PIP_PREFIX=$(pwd)/.pip_packages

    export PYTHONPATH="$PIP_PREFIX/${pkgs.python3.sitePackages}:$PYTHONPATH"

    export PATH="$PIP_PREFIX/bin:$PATH"

    unset SOURCE_DATE_EPOCH

    pip install ccxt
  '';
}
