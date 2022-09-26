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
        self.datapathlist:Topo=[0,0,0,0,0,0,0,0,0,0]
        
        self.dplist={}
        self.path:list=[]
        self.disarray=[]
        
        '''
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
        '''
        
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
            self.handle_lldp(datapath, pkt_lldp)
        
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            self.logger.info('arp PackIn')
 
            self.handle_arp(datapath, pkt_arp)
            
    
    def handle_lldp(self, datapath,pkt_lldp):

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
        portlist={}
        for k,v in Topo.port.items():
            portlist[k]=v
        
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
            for j,i in portlist.items():
                if self.disarray[i-1] > self.disarray[next]+self.datapathlist[next].portcost[j]:
                    self.disarray[i-1]=self.disarray[next]+self.datapathlist[next].portcost[j]
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
                dijkarray[v-1]=self.datapathlist[start].portcost[k]

        return dijkarray
    
    def send_port_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)
    
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
       
 
       
        
        temp = Topo(datapath.id)
        
        self.datapathlist[datapath.id-1]=temp
        for stat in ev.msg.body:
            if stat.port_no < ofproto.OFPP_MAX:
                temp.addport(stat.port_no,0)
                self.send_lldp_packet(datapath, stat.port_no, stat.hw_addr)
    
    def send_lldp_packet(self, datapath, port_no, hw_addr):
        ofp = datapath.ofproto
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_LLDP,src=hw_addr ,dst=lldp.LLDP_MAC_NEAREST_BRIDGE))
 
        tlv_chassis_id = lldp.ChassisID(subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED, chassis_id=str(datapath.id).encode('utf-8'))
        tlv_port_id = lldp.PortID(subtype=lldp.PortID.SUB_LOCALLY_ASSIGNED, port_id=str(port_no).encode('utf-8'))
        tlv_ttl = lldp.TTL(ttl=10)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_end)
        pkt.add_protocol(lldp.lldp(tlvs))
        pkt.serialize()
 
        data = pkt.data
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=port_no)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofp.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=data)
        datapath.send_msg(out)

    def sned_port_txbyte_req(self,datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)
    
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        ports = []
        dpid = ev.msg.datapath.id
        for stat in ev.msg.body:
            ports.append('port_no=%d '
                        'rx_packets=%d tx_packets=%d '
                        'rx_bytes=%d tx_bytes=%d '
                        'rx_dropped=%d tx_dropped=%d '
                        'rx_errors=%d tx_errors=%d '
                        'rx_frame_err=%d rx_over_err=%d rx_crc_err=%d '
                        'collisions=%d duration_sec=%d duration_nsec=%d' %
                        (stat.port_no,
                        stat.rx_packets, stat.tx_packets,
                        stat.rx_bytes, stat.tx_bytes,
                        stat.rx_dropped, stat.tx_dropped,
                        stat.rx_errors, stat.tx_errors,
                        stat.rx_frame_err, stat.rx_over_err,
                        stat.rx_crc_err, stat.collisions,
                        stat.duration_sec, stat.duration_nsec))
            self.datapathlist[dpid].modportcost(stat.port_no,stat.tx_bytes/1250000) #125M total bandwidth
        self.logger.debug('PortStats: %s', ports)


    def monitor(self):
        while True:
            if len(self.dplist)==10:
                for dp in self.dplist.values():
                    self.send_port_stats_request(dp)
                hub.sleep(5)    
                print('Topology Finish')
                break
            hub.sleep(5)
        while True:
            for dp in self.dplist.values():
                self.sned_port_txbyte_req(dp)
            hub.sleep(5)

            
        
        
        
        
        
        
    
    

class Topo:
    switch:int
    port:dict
    portcost:dict
    def __init__(self,dpid:int):
        self.port={}
        self.portcost={}
        self.switch=dpid
    
    def addport(self,outport,nextdp):
        self.port[outport]=nextdp
        self.portcost[outport]=0
    def modport(self,outport,nextdp):
        if self.port[outport]==0:
            self.port[outport]=nextdp
    def modportcost(self,port,cost):
        self.portcost[port]=cost - self.portcost[port]