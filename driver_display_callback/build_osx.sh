# ARNOLD_HOME needs to be set for CMake to find the proper files for building.

if [ -d build ]; then
	echo "Removing existing build";
	RM -rf build;
fi

mkdir -p build;
cd build;
cmake .. -G "CodeBlocks - Unix Makefiles"
make -j
