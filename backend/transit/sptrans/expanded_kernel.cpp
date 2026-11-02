// Exact bounded-cost enumeration. Prefixes are merged only when every legal
// continuation is shared; five distinct sequences then dominate later prefixes.
#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <stdexcept>
namespace {
struct Ride { int id,pattern,origin,destination,boarding,alighting; double seconds; };
struct Walk { int id,origin,destination,internal; double seconds,meters; };
struct Pattern { int service,rail; double wait; };
struct Path {
 std::array<int,9> edges{},patterns{};
 std::array<int,10> walks{};
 int length=0,units=0,destination=0;
 double seconds=0,walking=0;
};
struct Key {
 std::array<int,9> visited{};
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
 std::vector<int> limits;
 bool filling=false;
 double buffer;int origin=0,ceiling=8;
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
  // bucket below: at most two future bus services fit in the remaining budget.
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
  for(auto&old:bucket)if(same(p,old)){if(better(p,old))old=p;replaced=true;break;}
  if(!replaced)bucket.push_back(p);
  std::sort(bucket.begin(),bucket.end(),[&](const auto&a,const auto&b){return better(a,b);});
  int future_buses=(ceiling-p.units)/3;
  if(p.length==1&&!patterns[p.patterns[0]].rail){
   // Each prefix uses a different bus service; a suffix can exclude at most q.
   if(bucket.size()>size_t(5+future_buses))bucket.resize(5+future_buses);
  }else if(future_buses==1&&!terminal(p)){
   // Exact 1-exclusion representative family: retain the five best prefixes,
   // and the five best avoiding each bus appearing in those initial five.
   // Any other forbidden bus leaves the initial five entirely feasible.
   std::vector<int> forbidden;
   for(size_t n=0;n<std::min(size_t(5),bucket.size());n++)for(int i=0;i<bucket[n].length;i++)
    if(!patterns[bucket[n].patterns[i]].rail)forbidden.push_back(patterns[bucket[n].patterns[i]].service);
   std::sort(forbidden.begin(),forbidden.end());forbidden.erase(std::unique(forbidden.begin(),forbidden.end()),forbidden.end());
   std::vector<bool> selected(bucket.size(),false);for(size_t i=0;i<std::min(size_t(5),bucket.size());i++)selected[i]=true;
   for(int service:forbidden){int count=0;for(size_t i=0;i<bucket.size()&&count<5;i++){
    bool blocked=false;for(int j=0;j<bucket[i].length;j++)if(patterns[bucket[i].patterns[j]].service==service)blocked=true;
    if(!blocked){selected[i]=true;count++;}
   }}
   size_t out=0;for(size_t i=0;i<bucket.size();i++)if(selected[i])bucket[out++]=bucket[i];bucket.resize(out);
  }else if(bucket.size()>5)bucket.resize(5);
 }
 bool repeated(const Path&p,int pattern)const{
  for(int i=0;i<p.length;i++)if(patterns[p.patterns[i]].service==patterns[pattern].service)return true;
  return false;
 }
 void integer(uint32_t value){for(int i=0;i<4;i++)output.push_back((value>>(8*i))&255);}
 void seed(const unsigned char*data,uint64_t length){
  baseline.assign(outgoing.size(),{});original.assign(outgoing.size(),{});limits.assign(outgoing.size(),8);filling=true;
  uint64_t offset=0;
  auto integer_in=[&](){if(offset+4>length)throw std::invalid_argument("Truncated baseline");uint32_t v=0;for(int i=0;i<4;i++)v|=uint32_t(data[offset++])<<(8*i);return v;};
  while(offset<length){
   auto dest=integer_in(),size=integer_in();uint64_t end=offset+size;
   if(dest>=outgoing.size()||!size||end>length)throw std::invalid_argument("Invalid baseline row");
   int count=data[offset++];if(count<1||count>5)throw std::invalid_argument("Invalid baseline count");
   if(count==5){limits[dest]=-1;offset=end;continue;}
   original[dest].assign(data+offset,data+end);int minimum=9;
   for(int n=0;n<count;n++){
    if(offset+2>end)throw std::invalid_argument("Invalid baseline path");
    Path p;p.length=data[offset++];p.units=data[offset++];p.destination=dest;
    if(p.length<1||p.length>9||p.units>3)throw std::invalid_argument("Baseline must have cost at most one");
    minimum=std::min(minimum,p.units);p.walks[0]=integer_in();
    for(int i=0;i<p.length;i++){
     p.edges[i]=integer_in();if(p.edges[i]<1||p.edges[i]>=int(rides.size()))throw std::invalid_argument("Invalid ride");
     p.patterns[i]=rides[p.edges[i]].pattern;if(i)p.walks[i]=integer_in();
    }
    p.walks[9]=integer_in();baseline[dest].push_back(p);
   }
   if(offset!=end)throw std::invalid_argument("Invalid baseline size");
   limits[dest]=std::min(8,minimum+3);
  }
 }
 void generate(int start,int limit){
  if(limit<0||limit>8||start<0||start>=int(outgoing.size()))throw std::invalid_argument("Invalid origin or ceiling");
  origin=start;ceiling=limit;output.clear();
  std::vector<Bucket> finish(outgoing.size()),answers(outgoing.size());
  std::array<States,9> frontier;
  auto reached=[&](const Path&p){
   if(p.destination==origin)return;
   offer(finish[p.destination],p,true);
   if(!terminal(p))keep(frontier[p.units],p);
  };
  auto initial=[&](int stop,int walk,double seconds){
   for(auto& group:outgoing[stop])for(int eid:group.second){
    auto&e=rides[eid];Path p;p.edges[0]=eid;p.patterns[0]=e.pattern;p.length=1;p.destination=e.destination;
    p.walks[0]=walk;p.walking=seconds;p.seconds=seconds+e.seconds+patterns[e.pattern].wait;reached(p);
   }
  };
  initial(start,0,0);
  for(int wid:foot[start])if(walks[wid].internal)initial(walks[wid].destination,wid,walks[wid].seconds);
  for(int units=0;units<ceiling;units++){
   States boarding,templates;
   for(auto& entry:frontier[units])for(const Path&p:entry.second){
    keep(boarding,p,1);
    for(int wid:foot[p.destination]){
     const auto&w=walks[wid];if(!w.internal&&units+3>ceiling)continue;
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
     if(p.units+cost>ceiling)continue;
     Path q=p;q.patterns[q.length]=pattern;q.length++;q.units+=cost;
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
   auto accept=[&](const Path&q){if(!filling||(q.units>3&&q.units<=limits[q.destination]))offer(answers[q.destination],q,true);};
   accept(p);
   for(int wid:foot[p.destination]){
    auto&w=walks[wid];Path q=p;q.destination=w.destination;q.seconds+=w.seconds;q.walking+=w.seconds;q.walks[9]=wid;
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
    integer(p.walks[9]);
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
  e->outgoing.resize(stops);e->foot.resize(stops);e->buffer=buffer;
  for(int i=1;i<nr;i++)e->outgoing[e->rides[i].origin][e->rides[i].pattern].push_back(i);
  for(int i=1;i<nw;i++)e->foot[e->walks[i].origin].push_back(i);
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
const char* pap_error(){return error.c_str();}
void pap_free(void*ptr){delete static_cast<Engine*>(ptr);}
}
