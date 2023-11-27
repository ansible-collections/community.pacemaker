if [ ! -f /root/fence_agents.success ]; then
        yum install -y git autoconf automake corosynclib-devel flex flex-devel \
                libtool gcc-c++ make nss-devel libcurl-devel libxml2-devel libuuid-devel \
                openssl openssl-devel pexpect python3 python3-devel libvirt-devel libqb-devel byacc
        pip3 install pexpect pycurl requests
        git clone https://github.com/ClusterLabs/fence-agents.git
        cd fence-agents
        ./autogen.sh && ./configure
        make
        make install && touch /root/fence_agents.success
else
        echo "fence agents already installed"
fi;
