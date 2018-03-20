#!/usr/bin/python
import sys
import os
import logging
import threading
from time import sleep
import kazoo.exceptions
from kazoo.client import KazooClient

my_condition = threading.Condition()

result_file = '/tmp/zk_work/zk_file'

def seq_callback(seq):
    print '****', seq
    my_condition.acquire()
    my_condition.notify()
    my_condition.release()


def get_count(zk):
    try:
        info = zk.get('/count')
    except:
        print 'get some exception'

    '''
        info is Tuple (value, ZnodeStat) 
    '''
    return int(info[0])

def set_count(zk,count):
    try:
        zk.set('/count',str(count))
    except :
        print 'get some exception'

def init_callback(node):
    my_condition.acquire()
    my_condition.notify()
    my_condition.release()
    pass

def init_zk(zk):

    try:
        zk.get('/count')
    except kazoo.exceptions.NoNodeError:
        #create count
        my_condition.acquire()
        cr_lock = zk.exists('/init_lock',init_callback)
        if cr_lock is None:
            zk.create('/init_lock')
            zk.create('/count','10000')
            zk.create('lock')
            zk.delete('/init_lock')
        else:
            my_condition.wait()
        my_condition.release()
    except:
        pass


def main():
    zk = KazooClient('10.10.10.11:2181,10.10.10.12:2181,10.10.10.13:2181')
    #zk = KazooClient('192.168.184.128:2181,192.168.184.128:2182,192.168.184.128:2183')
    zk.start()

    init_zk(zk)

    env_dist = os.environ
    my_ip = env_dist.get('MY_IP')

    while True:

        #create my squence
        my_seq = zk.create('/lock/seq', ephemeral=True, sequence=True)
        print 'my seq:' + my_seq

        #get all the squences now,and sort them
        seq_list = zk.get_children('/lock')


        #get my squence index
        seq_list.sort(key=lambda x:x[3:])

        for n in range(len(seq_list)):
            seq_list[n] = '/lock/' + seq_list[n]


        #if my seuence is not 0, wait for the sequence deletion in front of me
        my_index = seq_list.index(my_seq)
        if  my_index is not 0:
            print 'wait ' + seq_list[my_index - 1]

            my_condition.acquire()
            ret = zk.exists(seq_list[my_index - 1],seq_callback)
            if ret is not None:
                print 'wait'
                my_condition.wait()
                print 'awake'
            my_condition.release()


        #write file
        count = get_count(zk)
        print my_ip + ': ' + str(count)
        with open(result_file,'a+') as f:
            f.write(my_ip + ': ' + str(count) + "\n")
        if count <= 0:
            break
        set_count(zk,count - 1)

        #delete my seq
        zk.delete(my_seq)
        print 'del' + my_seq
        #sleep 1 second

        #sleep(0.01)

    zk.stop()
    zk.close()

if __name__ == '__main__':
    sys.exit(main())