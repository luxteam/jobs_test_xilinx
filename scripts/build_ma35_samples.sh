#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Error: Script requires exactly one argument - build directory path"
    exit 1
fi

patch_content='diff --git a/CMakeLists.txt b/CMakeLists.txt
--- a/CMakeLists.txt	(revision 08e670ead7e6f8442a3ee6fc81725eee847b74e7)
+++ b/CMakeLists.txt	(date 1748613813269)
@@ -20,5 +20,5 @@
 add_subdirectory (scaler)
 add_subdirectory (encoder)
 add_subdirectory (transcoder)
-add_subdirectory (ml)
+#add_subdirectory (ml)

'


build_dir=$(realpath $1)
mkdir -p "$build_dir" || exit 1
cd "$build_dir" || exit 1
rm -rf *
mkdir src bin build
cp -r /opt/amd/ama/ma35/examples/xma/* ./src/
# Create temporary patch file
temp_patch_file="tmp.patch"
echo "$patch_content" > "$temp_patch_file"

# Apply patch
patch -p1 -d ./src/ < "$temp_patch_file"
rm "$temp_patch_file"

cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_MAKE_PROGRAM=ninja -G Ninja -S "$build_dir/src" -B "$build_dir/build"
cmake --build "$build_dir/build" --target clean -j 14
cmake --build "$build_dir/build" --target all -j 14
cp "$build_dir/build/encoder/ma35_encoder_app" "$build_dir/bin"
cp "$build_dir/build/decoder/ma35_decoder_app" "$build_dir/bin"
cp "$build_dir/build/scaler/ma35_scaler_app" "$build_dir/bin"
cp "$build_dir/build/transcoder/ma35_transcoder_app" "$build_dir/bin"