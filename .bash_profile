# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

# User specific environment and startup programs

PATH=$PATH:$HOME/bin

if [ -x /bin/ssh-add ] ; then
	MYNAME=`/usr/bin/whoami`
	if [ -f ~/.ssh/${MYNAME}_at_linkedin.com_ssh_key ] ; then
        /usr/bin/keychain ~/.ssh/${MYNAME}_at_linkedin.com_ssh_key
      	. ~/.keychain/`hostname`-sh
	fi
fi

export JAVA_HOME=/export/apps/jdk/JDK-11_0_10_9-msft
export JDK_HOME=/export/apps/jdk/JDK-11_0_10_9-msft
export NLS_LANG=American_America.UTF8


export PATH=$PATH:$JAVA_HOME/bin:/usr/local/bin:/usr/local/mysql/bin:/usr/local/linkedin/bin:/export/content/granular/bin/
