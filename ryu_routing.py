import re
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types

from ryu.lib.packet import ethernet, ether_types,lldp,packet,arp
from ryu import utils
from ryu.lib import hub
from operator import attrgetter
import re


class ryu_shortestPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    
    



    def __init__(self, *args, **kwargs):
        super(ryu_shortestPathRouting, self).__init__(*args, **kwargs)
        
        self.stack=[]
        #self.datapathlist:Topo=[0,0,0,0,0,0,0,0,0,0]
        self.datapathlist:Topo=[]
        self.dplist={}
        self.path:list=[]
        self.disarray=[]
        
        
        temp=Topo(1)
        
        temp.addport(2,5)
        temp.addport(3,6)
        self.datapathlist.append(temp)
        temp=Topo(2)
        
        temp.addport(2,5)
        self.datapathlist.append(temp)
        temp.addport(3,6)
        temp=Topo(3)
        
        temp.addport(2,7)
        temp.addport(3,8)
        self.datapathlist.append(temp)
        temp=Topo(4)
        
        temp.addport(2,7)
        temp.addport(3,8)
        self.datapathlist.append(temp)
        temp=Topo(5)
        temp.addport(1,1)
        temp.addport(2,2)
        temp.addport(3,9)
        self.datapathlist.append(temp)
        temp=Topo(6)
        temp.addport(1,1)
        temp.addport(2,2)
        temp.addport(3,10)
        self.datapathlist.append(temp)
        temp=Topo(7)
        temp.addport(1,3)
        temp.addport(2,4)
        temp.addport(3,9)
        self.datapathlist.append(temp)
        temp=Topo(8)
        temp.addport(1,3)
        temp.addport(2,4)
        temp.addport(3,10)
        self.datapathlist.append(temp)
        temp=Topo(9)
        temp.addport(1,5)
        temp.addport(2,7)
        self.datapathlist.append(temp)
        temp=Topo(10)
        temp.addport(1,6)
        temp.addport(2,8)
        self.datapathlist.append(temp)
        
        
        self.monitor_thread = hub.spawn(self.monitor)
        
        
        
    

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def tablemiss_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0,match, actions)
        '''
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_LLDP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 0, match, actions)
        '''
        

        if datapath not in self.dplist:
            self.dplist[datapath.id]=datapath
            
        
    
    def add_flow(self, datapath, priority, match, actions, buff_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data) 
        
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)
        if not pkt_ethernet:
            return
 
        pkt_lldp = pkt.get_protocol(lldp.lldp)
        if pkt_lldp:
            self.handle_lldp(datapath, port, pkt_ethernet, pkt_lldp)
        
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            self.logger.info('arp PackIn')
 
            self.handle_arp(datapath, pkt_arp)
            
    
    def handle_lldp(self, datapath, port, pkt_lldp):

        #print(pkt_lldp.tlvs[1].port_id[0]-48)
        #print(int(bytes.decode(pkt_lldp.tlvs[0].chassis_id,encoding='utf-8')))
        self.datapathlist[int(bytes.decode(pkt_lldp.tlvs[0].chassis_id,encoding='utf-8'))-1].addport(int(bytes.decode(pkt_lldp.tlvs[1].port_id,encoding="utf-8")),datapath.id)

    def handle_arp(self, datapath, pkt_arp):
        parser = datapath.ofproto_parser
        src = pkt_arp.src_ip
        dst = pkt_arp.dst_ip
        src = re.search('\d\Z',src).group()   #get ip host(class c)
        dst = re.search('\d\Z',dst).group()
        print('get a arp ',src,' to ',dst)
        self.setFlowEntry(src,dst,parser)


        return
    def setFlowEntry(self,src,dst,parser):
        
        arptodstmatch = parser.OFPMatch(eth_type=0x0806, arp_spa='10.0.0.1' + src, arp_tpa='10.0.0.1'+dst)
        arptosrcmatch = parser.OFPMatch(eth_type=0x0806, arp_spa='10.0.0.1' + dst, arp_tpa='10.0.0.1'+src)
        pkttodstmatch = parser.OFPMatch(eth_type=0x0800, ipv4_dst='10.0.0.1'+dst)
        pkttosrcmatch = parser.OFPMatch(eth_type=0x0800, ipv4_dst='10.0.0.1'+src)
        self.dijk_routing(int(src),int(dst))
        
        step = len(self.path[int(dst)])
        print('path = ',self.path[int(dst)])
        count = 0
        for i in self.path[int(dst)]:
            if count+1<step: 
                
                outport = self.serachSwitchWhichPort(self.datapathlist[i-1],self.path[int(dst)][count+1])
                if outport==None:
                    print('port error')
                else:
                    action = [parser.OFPActionOutput(port=outport)]
                
            else:
                action = [parser.OFPActionOutput(port=1)]
            self.add_flow(self.dplist[i],5,arptodstmatch,action)
            self.add_flow(self.dplist[i],4,pkttodstmatch,action)

            if count==0:
                action = [parser.OFPActionOutput(port=1)]
            else:
                
                outport = self.serachSwitchWhichPort(self.datapathlist[i-1],self.path[int(dst)][count-1])
                if outport == None:
                    print('port error')
                else:
                    action = [parser.OFPActionOutput(port=outport)]
            self.add_flow(self.dplist[i],5,arptosrcmatch,action)
            self.add_flow(self.dplist[i],4,pkttosrcmatch,action)


            count +=1
                
                
        return
    
    def searchPort(self,Topo):
        portlist=[]
        for k,v in Topo.port.items():
            portlist.append(v)
        
        return portlist
    
    def serachSwitchWhichPort(self,Topo,switch):
        for k,v in Topo.port.items():
            if v==switch:
                return k
        
        return None
        
        


    def dijk_routing(self,start,end):
        self.disarray.clear()
        self.disarray=self.dijk_array(start)
        print('start:',start,'distance',self.disarray)
        visited=[0,0,0,0,0,0,0,0,0,0]
        self.initPath(start)
        
        visited[start]=1
        while(True):
            if visited[end] !=0:
                break
            min = 9
            count=0
            for i in self.disarray:
                if i!=0 and i<min and visited[count]!=1:
                    min = i
                    next = count
                count +=1

            visited[next] = 1
            
            #print('visted point =',next+1)
            portlist = self.searchPort(self.datapathlist[next])
            for i in portlist:
                if self.disarray[i-1] > self.disarray[next]+1:
                    self.disarray[i-1]=self.disarray[next]+1
                    self.path[i-1]=self.path[next].copy()
                    self.path[i-1].append(i)
                    #print('update',i,'distance=',self.disarray[next]+1)
        



        
    def initPath(self,start):
        self.path.clear()
        self.path=[[]for _ in range(0,10)]
        
        startnext = self.searchPort(self.datapathlist[start])
        self.path[start]=[start]
        for i in startnext:
            self.path[i-1].append(start+1)
            self.path[i-1].append(i)
        
    


    def dijk_array(self,start):
        maxdp = len(self.dplist)
        
        dijkarray=[9 for _ in range(maxdp)]
        
        dijkarray[start]=0
            
        for k,v in self.datapathlist[start].port.items():
            
            if v!=0:
                dijkarray[v-1]=1

        return dijkarray
    
    def display(self,array):
        for i in array:
            if i.port:
                self.logger.info('-----  -----  --------')
                self.logger.info('dpid   port   neighbor')
                for k,v in i.port.items():
                    self.logger.info('%05d %05d %7s',i.switch,k,v)
                self.logger.info('----------------------')
        '''
        for i in range(0,10):
            for j in range(0,10):
                self.logger.info('%d')
        '''

   
        

    
   
    
    def handle_lldp(self, datapath, port, pkt_ethernet, pkt_lldp):

        #print(pkt_lldp.tlvs[1].port_id[0]-48)
        #print(int(bytes.decode(pkt_lldp.tlvs[0].chassis_id,encoding='utf-8')))
        self.datapathlist[int(bytes.decode(pkt_lldp.tlvs[0].chassis_id,encoding='utf-8'))-1].addport(int(bytes.decode(pkt_lldp.tlvs[1].port_id,encoding="utf-8")),datapath.id)
    
    def monitor(self):
        while True:
            
                
        
            hub.sleep(5)
            #self.display(self.datapathlist)
            
        
        
        
        
        
        
    
    

class Topo:
    switch:int
    port:dict
    def __init__(self,dpid:int):
        self.port={}
        self.switch=dpid
    
    def addport(self,outport,nextdp):
        self.port[outport]=nextdp
    def modport(self,outport,nextdp):
    
        if self.port[outport]==0:
            self.port[outport]=nextdp