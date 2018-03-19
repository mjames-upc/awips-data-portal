#!/bin/bash
#
# This script is designed for deployment on CentOS/RHEL Linux servers but will
# run on any operating system and architecture supporting Conda Python environments
#
# 1. install miniconda2
#    (this is managed with environment.yml for continuous integration)
# 
# wget https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
# chmod 755 Miniconda2-latest-Linux-x86_64.sh
# ./Miniconda2-latest-Linux-x86_64.sh
#
#   do NOT append to .bashrc since it would superceed /awips2/python 
#   for the awips account - only src conda python from these scripts
#

# 2. clone awips-pdata-portal
# git clone https://github.com/mjames-upc/awips-data-portal.git 
# cd awips-data-portal
# git checkout -t -b python_portal origin/python_portal

# 3. add miniconda to path
PATH="/home/awips/miniconda2/bin:$PATH"

#conda env create -f environment.yml

source activate awips-data-portal
python portal.py
