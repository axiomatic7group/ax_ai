## Getting Started with llama.cpp 
This guide provides a quick walkthrough for setting up and running llama.cpp on your local machine using the command line.
## 1. Installation
First, clone the repository and navigate into the project directory: 

git clone https://github.com
cd llama.cpp

## 2. Building the Project
Use cmake to configure and build the binaries.

* Standard Build:

cmake -B build
cmake --build build --config Release

* With NVIDIA GPU (CUDA) Support:

cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release


## 3. Running the Server
Navigate to the output directory to start the server. You can download and load models directly from Hugging Face using the -hf flag.

cd build/bin
# General Syntax
./llama-server -hf <developer>/<model_name>
# Example: Loading Ministral-3B
./llama-server -hf mistralai/Ministral-3-3B-Instruct-2512-GGUF:Q4_K_M

## Resources

* Model Browser: Find more GGUF models on Hugging Face.
* Official Documentation: Refer to the llama.cpp GitHub for advanced configuration.

