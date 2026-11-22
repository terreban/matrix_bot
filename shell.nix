{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    (python313.withPackages (ps: with ps; [
      pip
      build
    ]))
  ];


}
