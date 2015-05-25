#!/bin/sh
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" && brew install hg git python wxpython && pip install -r requirements.txt
