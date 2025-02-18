# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
{
  pkgs ? import ./pkgs.nix {},
  yosys ? import ./yosys.nix { inherit pkgs; },
}:

with pkgs; clangStdenv.mkDerivation rec {
  name = "yosys-lighter";
  dylibs = ["lighter"];

  src = fetchFromGitHub {
    owner = "aucohl";
    repo = "lighter";
    rev = "b8e7d4ece5d6e22ab62c03eead761c736dbcaf3c";
    sha256 = "sha256-gftQwWrq7KVVQXfb/SThOvbEJK0DoPpiQ3f3X1thBiQ=";
  };
  propagatedBuildInputs = [
    yosys
    libedit
    libbsd
    zlib
  ];

  buildInputs = [
    yosys.py3
  ];

  buildPhase = ''
  ${yosys}/bin/yosys-config --build lighter.so src/clock_gating_plugin.cc
  '';

  installPhase = ''
  mkdir -p $out/share/yosys/plugins
  cp lighter.so $out/share/yosys/plugins

  mkdir -p $out/bin
  cat << HD > $out/bin/lighter_files
  #!/bin/sh
  if [ "\$1" = "" ]; then
    echo "Usage: \$0 <scl>" >> /dev/stderr
    exit 1
  fi
  find $out/share/lighter_maps/\$1 -type f
  HD
  chmod +x $out/bin/lighter_files

  mkdir -p $out/share/lighter_maps
  cp -r platform/* $out/share/lighter_maps
  rm -rf $out/share/lighter_maps/**/*.lib
  rm -rf $out/share/lighter_maps/**/*_blackbox.v
  '';

  computed_PATH = lib.makeBinPath propagatedBuildInputs;
  makeWrapperArgs = [
    "--prefix PATH : ${computed_PATH}"
  ];
}