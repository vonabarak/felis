#!/bin/sh

SRC="/usr/src"
SRC_ZFS="zroot/usr/src"
WORLD="/opt/world"
WORLD_ZFS="zroot/opt/world"
OBJ="/usr/obj"

DOMAIN="vonabarak.ru"
DNS1="192.168.172.1"
DNS2="2a01:4f8:a0:228c:1:2::"

cleansrc(){
    echo Removing old files from ${OBJ}...
    rm -rf ${OBJ}/usr/src
    chflags -R noschg ${OBJ}/base/
    rm -rf ${OBJ}/base
    rm -rf ${OBJ}/doc
    rm -rf ${OBJ}/tests
    rm ${OBJ}/tests.txz
    rm ${OBJ}/doc.txz
    rm ${OBJ}/base.txz
    rm ${OBJ}/base-dbg.txz
}

updatesrc(){
    echo Updating source tree in ${SRC}...
    zfs set readonly=off ${SRC_ZFS} || exit 2
    cd ${SRC}
    svnlite update || exit 2
    zfs set readonly=on ${SRC_ZFS} || exit 2
}

buildworld(){
    cleansrc
    echo Building world...
    cd ${SRC}
    make -j4 buildworld || exit 3
}

packageworld(){
    echo Making world package...
    cd ${SRC}
    DISTDIR=${OBJ} make distributeworld || exit 4
    DISTDIR=${OBJ} make packageworld || exit 4
}

stopjails(){
    echo Stopping jails...
    service jail stop
}

startjails(){
    echo Starting jails...
    service jail start
}

backupworld(){
    echo Backuping old world via zfs snapshot...
    zfs snapshot ${WORLD_ZFS}@`date "+%Y%m%d%H%M%S"` || exit 5
}

cleanworld(){
    echo Cleaning world destination...
    zfs set readonly=off ${WORLD_ZFS} || exit 7
    chflags -R noschg ${WORLD}/*
    rm -rf ${WORLD}/* || exit 7
}

installworld(){
    stopjails
    backupworld
    cleanworld
    echo Installing new world...
    cd ${WORLD}
    tar xvpf ${OBJ}/base.txz || exit 8
    # settting resolvers
    echo "search ${DOMAIN}" > ${WORLD}/etc/resolv.conf
    echo "nameserver ${DNS1}" >> ${WORLD}/etc/resolv.conf
    echo "nameserver ${DNS2}" >> ${WORLD}/etc/resolv.conf
    zfs set readonly=on ${WORLD_ZFS} || exit 8
    mv ${OBJ}/base.txz ${OBJ}/base-`date "+%Y%m%d%H%M%S"`.txz
    startjails
}

donemessage(){
    echo Done.
}

usage(){
    echo Usage:
    echo $0 target
    echo where target is one of: all, updatesrc, buildworld, packageworld, installworld
}

all(){
    updatesrc
    buildworld
    packageworld
    installworld
    donemessage
}

if [ $# -eq 1 ]; then
    case $1 in 
        all|updatesrc|buildworld|packageworld|installworld)
            $1
            ;;
        *)
            usage
            ;;
    esac
else
    usage
fi

