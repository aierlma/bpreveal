#!/usr/bin/env zsh
#SBATCH --job-name buildBpreveal
#SBATCH --ntasks=3
#SBATCH --nodes=1
#SBATCH --mem=10gb
#SBATCH --time=1:00:00
#SBATCH --output=log%j.log
#SBATCH --partition=gpu
#SBATCH --gres gpu:0

# This is a script that you can run on Cerebro (the cluster at Stowers)
# to install bpreveal. If you're not on a cluster, see the buildCondaLocal.zsh
# script.

################
# CHANGE THESE #
################
SHELL=bash
source /home/gq2899/.bashrc
conda deactivate
# I need to source my .shrc to get conda on the path.
# CHANGE this to your own shell rc file, or it may
# work without this line for you.

export SHELL_RC_FILE=/home/gq2899/.zshrc
# The location where you cloned the git repository.
# CHANGE to reflect your directory.
export BPREVEAL_DIR=/home/gq2899/bin/bpreveal

# -p if you're specifying a path, -n if you're specifying a name.
# CHANGE the environment name to your own preference.
export ENV_FLAG=-n
export ENV_NAME=bpreveal_404

# CHANGE this to conda if you don't have mamba installed.
# (I recommend using mamba; it's way faster.)
export CONDA_BIN=mamba
export PIP_BIN=pip

# Do you want to install Jupyter?
# Options: true or false
export INSTALL_JUPYTER=true

#Do you want the tools used for development?
# These are needed to run the code quality checks and build the html documentation.
# Options: true or false
export INSTALL_DEVTOOLS=false

# Do you want to install pydot and graphviz? This is needed to render an image from showModel.
export INSTALL_PYDOT=false

# Do you want to install some miscellaneous stuff that Charles likes?
# I recommend that you set this to False, as these are not necessary for
# anything in BPReveal.
export INSTALL_MISC=false

######################
# DON'T CHANGE BELOW #
######################

${SHELL} ${BPREVEAL_DIR}/etc/buildCondaSuite.zsh
