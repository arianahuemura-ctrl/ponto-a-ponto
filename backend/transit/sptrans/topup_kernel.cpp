// Exact bounded-cost enumeration. Prefixes are merged only when every legal
// continuation is shared; five distinct sequences then dominate later prefixes.
#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <stdexcept>
#include <queue>
#include <set>
#include <functional>
namespace {
struct Ride { int id,pattern,origin,destination,boarding,alighting; double seconds; };
struct Walk { int id,origin,destination,internal; double seconds,meters; };
struct Pattern { int service,rail; double wait; };
struct Path {
 std::array<int,13> edges{},patterns{};
 std::array<int,14> walks{};
 std::array<int,5> buses{};int bus_count=0;
 int length=0,units=0,destination=0;
 double seconds=0,walking=0;
};
struct Key {
 std::array<int,13> visited{};
 int stop=0,units=0,mode=0,pending=0,pattern=-1;
 bool operator==(const Key& b)const{return visited==b.visited&&stop==b.stop&&units==b.units&&mode==b.mode&&pending==b.pending&&pattern==b.pattern;}
};
struct Hash {size_t operator()(const Key& k)const{
 size_t h=0;for(int v:k.visited)h=h*1000003u+v;
 return ((((h*1000003u+k.stop)*17+k.units)*3+k.mode)*3+k.pending)*1000003u+k.pattern;
}};
using Bucket=std::vector<Path>;
using States=std::unordered_map<Key,Bucket,Hash>;
struct Engine {
 std::vector<Ride> rides;std::vector<Walk> walks;std::vector<Pattern> patterns;
 std::vector<std::unordered_map<int,std::vector<int>>> outgoing;
 std::vector<std::vector<int>> foot;
 std::vector<unsigned char> output;
 std::vector<Bucket> baseline;
 std::vector<std::vector<unsigned char>> original;
 std::vector<int> limits,final_limits;
 std::vector<std::unordered_map<int,int>> boarding_limits;
 std::vector<std::array<int,2>> boarding_prefix_limits,transfer_limits;
 std::vector<std::array<int,2>> remaining;
 std::vector<std::vector<int>> incoming,reverse_foot;
 bool filling=false;
 double buffer;int origin=0,ceiling=12,floor=8;
 bool better(const Path&a,const Path&b)const{
  if(a.units!=b.units)return a.units<b.units;
  if(a.seconds!=b.seconds)return a.seconds<b.seconds;
  if(a.walking!=b.walking)return a.walking<b.walking;
  if(a.edges!=b.edges)return a.edges<b.edges;
  return a.walks<b.walks;
 }
 bool same(const Path&a,const Path&b)const{
  if(a.length!=b.length)return false;
  for(int i=0;i<a.length;i++)if(patterns[a.patterns[i]].service!=patterns[b.patterns[i]].service)return false;
  return true;
 }
 void offer(Bucket& bucket,const Path&p,bool final=false){
  if(final){
   if(p.destination==origin)return;
   if(!bucket.empty()&&p.units>bucket.front().units+3)return;
   if(!bucket.empty()&&p.units<bucket.front().units)
    bucket.erase(std::remove_if(bucket.begin(),bucket.end(),[&](const Path& old){return old.units>p.units+3;}),bucket.end());
  }
  for(auto& old:bucket)if(same(p,old)){
   if(better(p,old)){old=p;std::sort(bucket.begin(),bucket.end(),[&](const auto&a,const auto&b){return better(a,b);});}return;
  }
  if(bucket.size()==5&&!better(p,bucket.back()))return;
  bucket.push_back(p);std::sort(bucket.begin(),bucket.end(),[&](const auto&a,const auto&b){return better(a,b);});
  if(bucket.size()>5)bucket.pop_back();
 }
 bool terminal(const Path&p)const{return p.units+(patterns[p.patterns[p.length-1]].rail?1:3)>ceiling;}
 Key key(const Path&p,int pending,int next_pattern=-1)const{
  Key k;k.stop=p.destination;k.units=p.units;k.pending=pending;k.pattern=next_pattern;
  k.mode=patterns[p.patterns[p.length-1]].rail;
  // Rail exclusions are kept exactly. Bus exclusions are represented by the
  // bucket below represents every exclusion set allowed by the remaining budget.
  if(!terminal(p)){
   int n=0;for(int i=0;i<p.length;i++)if(patterns[p.patterns[i]].rail)
    k.visited[n++]=patterns[p.patterns[i]].service+1;
   std::sort(k.visited.begin(),k.visited.begin()+n);
  }
  return k;
 }
 void keep(States& s,const Path&p,int pending=1,int next_pattern=-1){
  auto& bucket=s[key(p,pending,next_pattern)];
  bool replaced=false;
  for(auto&old:bucket)if(same(p,old)){if(!better(p,old))return;old=p;replaced=true;break;}
  if(!replaced)bucket.push_back(p);
  std::sort(bucket.begin(),bucket.end(),[&](const auto&a,const auto&b){return better(a,b);});
  if(bucket.size()<=5)return;
  int future_buses=(ceiling-p.units)/3;
  if(p.length==1&&!patterns[p.patterns[0]].rail){
   // Each prefix uses a different bus service; a suffix can exclude at most q.
   if(bucket.size()>size_t(5+future_buses))bucket.resize(5+future_buses);
  }else if(future_buses>0&&!terminal(p)){
   if(std::all_of(bucket.begin(),bucket.end(),[](const Path& p){return p.bus_count<=1;})){
    std::unordered_map<int,int> counts;size_t out=0;
    for(size_t i=0;i<bucket.size()&&out<size_t(5*(future_buses+1));i++){
     int service=bucket[i].bus_count?bucket[i].buses[0]:-1;
     if(counts[service]++<5)bucket[out++]=bucket[i];
    }
    bucket.resize(out);return;
   }
   // At most five bus services fit in the entire path. Stack arrays avoid
   // allocating a set for every prefix and every recursive exclusion query.
   std::vector<bool> selected(bucket.size(),false);
   std::array<int,4> excluded{};
   auto choose=[&](auto&& self,int depth)->void{
    int count=0,branches_size=0;std::array<int,25> branches{};
    for(size_t i=0;i<bucket.size()&&count<5;i++){
     const Path& path=bucket[i];bool blocked=false;
     for(int j=0;j<path.bus_count&&!blocked;j++)for(int k=0;k<depth;k++)if(path.buses[j]==excluded[k]){blocked=true;break;}
     if(blocked)continue;
     selected[i]=true;count++;
     if(depth<future_buses)for(int j=0;j<path.bus_count;j++)branches[branches_size++]=path.buses[j];
    }
    if(depth==future_buses||count<5)return;
    std::sort(branches.begin(),branches.begin()+branches_size);
    branches_size=std::unique(branches.begin(),branches.begin()+branches_size)-branches.begin();
    for(int i=0;i<branches_size;i++){excluded[depth]=branches[i];self(self,depth+1);}
   };
   choose(choose,0);size_t out=0;for(size_t i=0;i<bucket.size();i++)if(selected[i])bucket[out++]=bucket[i];bucket.resize(out);
  }else if(bucket.size()>5)bucket.resize(5);
 }
 bool repeated(const Path&p,int pattern)const{
  for(int i=0;i<p.length;i++)if(patterns[p.patterns[i]].service==patterns[pattern].service)return true;
  return false;
 }
 void integer(uint32_t value){for(int i=0;i<4;i++)output.push_back((value>>(8*i))&255);}
 void seed(const unsigned char*data,uint64_t length){
  baseline.assign(outgoing.size(),{});original.assign(outgoing.size(),{});limits.assign(outgoing.size(),12);filling=true;
  uint64_t offset=0;
  auto integer_in=[&](){if(offset+4>length)throw std::invalid_argument("Truncated baseline");uint32_t v=0;for(int i=0;i<4;i++)v|=uint32_t(data[offset++])<<(8*i);return v;};
  while(offset<length){
   auto dest=integer_in(),size=integer_in();uint64_t end=offset+size;
   if(dest>=outgoing.size()||!size||end>length)throw std::invalid_argument("Invalid baseline row");
   int count=data[offset++];if(count<1||count>5)throw std::invalid_argument("Invalid baseline count");
   if(count==5){limits[dest]=-1;offset=end;continue;}
   original[dest].assign(data+offset,data+end);int minimum=13;
   for(int n=0;n<count;n++){
    if(offset+2>end)throw std::invalid_argument("Invalid baseline path");
    Path p;p.length=data[offset++];p.units=data[offset++];p.destination=dest;
    if(p.length<1||p.length>13||p.units>floor)throw std::invalid_argument("Baseline exceeds completed cost");
    minimum=std::min(minimum,p.units);p.walks[0]=integer_in();
    for(int i=0;i<p.length;i++){
     p.edges[i]=integer_in();if(p.edges[i]<1||p.edges[i]>=int(rides.size()))throw std::invalid_argument("Invalid ride");
     p.patterns[i]=rides[p.edges[i]].pattern;if(i)p.walks[i]=integer_in();
     if(!patterns[p.patterns[i]].rail){if(p.bus_count==5)throw std::invalid_argument("Too many baseline buses");p.buses[p.bus_count++]=patterns[p.patterns[i]].service;}
    }
    p.walks[13]=integer_in();baseline[dest].push_back(p);
   }
   if(offset!=end)throw std::invalid_argument("Invalid baseline size");
   limits[dest]=std::min(12,minimum+3);
  }
 }
 void prepare_targets(){
  final_limits.assign(outgoing.size(),-1);
  remaining.assign(outgoing.size(),{-1,-1});
  std::vector<std::array<int,2>> boarding_limit(outgoing.size(),{-1,-1});
  for(size_t i=0;i<limits.size();i++)if(int(i)!=origin&&limits[i]>floor){
   int cap=std::min(ceiling,limits[i]);
   final_limits[i]=std::max(final_limits[i],cap);
   for(int wid:reverse_foot[i])final_limits[walks[wid].origin]=std::max(final_limits[walks[wid].origin],cap);
  }
  using Item=std::array<int,3>;std::priority_queue<Item> queue;
  auto offer_state=[&](int stop,int mode,int units){if(units>=0&&units>remaining[stop][mode]){remaining[stop][mode]=units;queue.push({units,stop,mode});}};
  for(size_t i=0;i<final_limits.size();i++)for(int mode=0;mode<2;mode++)offer_state(i,mode,final_limits[i]);
  while(!queue.empty()){
   auto item=queue.top();queue.pop();int units=item[0],stop=item[1],mode=item[2];
   if(units!=remaining[stop][mode])continue;
   for(int eid:incoming[stop]){
    const auto&r=rides[eid];if(patterns[r.pattern].rail!=mode)continue;
    if(units<=boarding_limit[r.origin][mode])continue;
    boarding_limit[r.origin][mode]=units;
    for(int previous=0;previous<2;previous++)offer_state(r.origin,previous,units-((previous&&mode)?1:3));
    for(int wid:reverse_foot[r.origin]){
     const auto&w=walks[wid];for(int previous=0;previous<2;previous++)offer_state(w.origin,previous,units-((w.internal&&previous&&mode)?1:3));
    }
   }
  }
  boarding_limits.clear();boarding_limits.resize(outgoing.size());
  boarding_prefix_limits.assign(outgoing.size(),{-1,-1});
  for(size_t stop=0;stop<outgoing.size();stop++)for(const auto& group:outgoing[stop]){
   int maximum=-1,mode=patterns[group.first].rail;
   for(int eid:group.second)if(rides[eid].destination!=origin)maximum=std::max(maximum,remaining[rides[eid].destination][mode]);
   boarding_limits[stop][group.first]=maximum;
   boarding_prefix_limits[stop][0]=std::max(boarding_prefix_limits[stop][0],maximum-3);
   boarding_prefix_limits[stop][1]=std::max(boarding_prefix_limits[stop][1],maximum-(mode?1:3));
  }
  transfer_limits=boarding_prefix_limits;
  for(size_t stop=0;stop<foot.size();stop++)for(int wid:foot[stop]){
   const auto&w=walks[wid];for(int mode=0;mode<2;mode++)transfer_limits[stop][mode]=std::max(transfer_limits[stop][mode],boarding_prefix_limits[w.destination][w.internal?mode:0]);
  }
 }
 void generate(int start,int limit){
  if(limit<0||limit>12||start<0||start>=int(outgoing.size()))throw std::invalid_argument("Invalid origin or ceiling");
  origin=start;ceiling=limit;output.clear();
  if(filling)prepare_targets();
  std::vector<Bucket> finish(outgoing.size()),answers(outgoing.size());
  std::array<States,13> frontier;
  auto reached=[&](const Path&p){
   if(p.destination==origin)return;
   if(!filling||p.units<=final_limits[p.destination])offer(finish[p.destination],p,true);
   if(!terminal(p)&&(!filling||p.units<=transfer_limits[p.destination][patterns[p.patterns[p.length-1]].rail]))keep(frontier[p.units],p);
  };
  auto initial=[&](int stop,int walk,double seconds){
   for(auto& group:outgoing[stop])for(int eid:group.second){
    auto&e=rides[eid];Path p;p.edges[0]=eid;p.patterns[0]=e.pattern;p.length=1;p.destination=e.destination;
    if(!patterns[e.pattern].rail)p.buses[p.bus_count++]=patterns[e.pattern].service;
    p.walks[0]=walk;p.walking=seconds;p.seconds=seconds+e.seconds+patterns[e.pattern].wait;reached(p);
   }
  };
  initial(start,0,0);
  for(int wid:foot[start])if(walks[wid].internal)initial(walks[wid].destination,wid,walks[wid].seconds);
  for(int units=0;units<ceiling;units++){
   States boarding,templates;
   for(auto& entry:frontier[units])for(const Path&p:entry.second){
    int mode=patterns[p.patterns[p.length-1]].rail;
    if(!filling||p.units<=boarding_prefix_limits[p.destination][mode])keep(boarding,p,1);
    for(int wid:foot[p.destination]){
     const auto&w=walks[wid];if(!w.internal&&units+3>ceiling)continue;
     if(filling&&p.units>boarding_prefix_limits[w.destination][w.internal?mode:0])continue;
     Path q=p;q.destination=w.destination;q.seconds+=w.seconds;q.walking+=w.seconds;
     q.walks[q.length]=wid;keep(boarding,q,w.internal?1:0);
    }
   }
   frontier[units].clear();frontier[units].rehash(0);
   for(auto& entry:boarding)for(const Path&p:entry.second){
    for(auto& group:outgoing[p.destination]){
     int pattern=group.first;
     if(repeated(p,pattern))continue;
     int cost=entry.first.pending&&patterns[p.patterns[p.length-1]].rail&&patterns[pattern].rail?1:3;
     if(p.units+cost>ceiling||(filling&&p.units+cost>boarding_limits[p.destination].at(pattern)))continue;
     Path q=p;q.patterns[q.length]=pattern;q.length++;q.units+=cost;
     if(!patterns[pattern].rail)q.buses[q.bus_count++]=patterns[pattern].service;
     q.seconds+=buffer+patterns[pattern].wait;
     keep(templates,q,1,pattern);
    }
   }
   boarding.clear();boarding.rehash(0);
   for(auto& entry:templates)for(const Path&p:entry.second){
    for(int eid:outgoing[p.destination].at(entry.first.pattern)){
     auto&e=rides[eid];Path q=p;q.edges[q.length-1]=eid;q.destination=e.destination;q.seconds+=e.seconds;reached(q);
    }
   }
  }
  // Walking has no further service choices. Five best sequences at an alighting
  // stop dominate any discarded sequence for every identical final walk.
  for(auto& bucket:finish)for(const Path&p:bucket){
   auto accept=[&](const Path&q){if(!filling||(q.units>floor&&q.units<=limits[q.destination]))offer(answers[q.destination],q,true);};
   accept(p);
   for(int wid:foot[p.destination]){
    auto&w=walks[wid];Path q=p;q.destination=w.destination;q.seconds+=w.seconds;q.walking+=w.seconds;q.walks[13]=wid;
    accept(q);
   }
  }
  for(uint32_t destination=0;destination<answers.size();destination++){
   auto bucket=answers[destination];if(bucket.empty())continue;
   size_t previous=0;
   if(filling){
    previous=baseline[destination].size();
    bucket.erase(std::remove_if(bucket.begin(),bucket.end(),[&](const Path&p){for(const auto&old:baseline[destination])if(same(p,old))return true;return false;}),bucket.end());
    if(bucket.size()>5-previous)bucket.resize(5-previous);
    if(bucket.empty())continue;
   }
   integer(destination);size_t length_pos=output.size();integer(0);size_t begin=output.size();output.push_back(previous+bucket.size());
   if(filling)output.insert(output.end(),original[destination].begin(),original[destination].end());
   for(const auto&p:bucket){
    output.push_back(p.length);output.push_back(p.units);integer(p.walks[0]);
    for(int i=0;i<p.length;i++){integer(p.edges[i]);if(i)integer(p.walks[i]);}
    integer(p.walks[13]);
   }
   uint32_t length=output.size()-begin;for(int i=0;i<4;i++)output[length_pos+i]=(length>>(8*i))&255;
  }
 }
};
static thread_local std::string error;
}
extern "C" {
void* pap_engine(const Ride*r,int nr,const Walk*w,int nw,const Pattern*p,int np,int stops,double buffer){
 try{
  auto*e=new Engine;e->rides.assign(r,r+nr);e->walks.assign(w,w+nw);e->patterns.assign(p,p+np);
  e->outgoing.resize(stops);e->foot.resize(stops);e->incoming.resize(stops);e->reverse_foot.resize(stops);e->buffer=buffer;
  for(int i=1;i<nr;i++){e->outgoing[e->rides[i].origin][e->rides[i].pattern].push_back(i);e->incoming[e->rides[i].destination].push_back(i);}
  for(int i=1;i<nw;i++){e->foot[e->walks[i].origin].push_back(i);e->reverse_foot[e->walks[i].destination].push_back(i);}
  return e;
 }catch(const std::exception&e){error=e.what();return nullptr;}
}
int pap_generate(void*ptr,int origin,int ceiling,const unsigned char**data,uint64_t*size){
 try{auto*e=static_cast<Engine*>(ptr);e->generate(origin,ceiling);*data=e->output.data();*size=e->output.size();return 0;}
 catch(const std::exception&e){error=e.what();return -1;}
}
int pap_baseline(void*ptr,const unsigned char*data,uint64_t size){
 try{static_cast<Engine*>(ptr)->seed(data,size);return 0;}catch(const std::exception&e){error=e.what();return -1;}
}
int pap_floor(void*ptr,int floor){
 if(floor<8||floor>12){error="Invalid completed cost";return -1;}
 static_cast<Engine*>(ptr)->floor=floor;return 0;
}
const char* pap_error(){return error.c_str();}
void pap_free(void*ptr){delete static_cast<Engine*>(ptr);}
}
