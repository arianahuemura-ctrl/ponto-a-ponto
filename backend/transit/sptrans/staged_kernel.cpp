// Offline enumeration. Only final OD answers are truncated, never the frontier.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>
#include <cmath>

struct Ride { int id, pattern, origin, destination, boarding, alighting; double seconds; };
struct Walk { int id, origin, destination, internal; double seconds, meters; };
struct Pattern { int service, rail; double wait; };
struct Path {
    std::array<int,4> edges{}, patterns{};
    std::array<int,5> walks{}; // access, three transfers, egress
    int length=0, units=0, destination=0;
    double seconds=0, walking=0;
};
struct Key {
    std::array<int,4> sequence{};
    int stop=0,units=0,pending=0;
    bool operator==(const Key& b)const{return sequence==b.sequence&&stop==b.stop&&units==b.units&&pending==b.pending;}
};
struct Hash { size_t operator()(const Key& k)const{
    size_t h=0; for(int v:k.sequence)h=h*1000003u+v;
    return ((h*1000003u+k.stop)*17+k.units)*3+k.pending;
}};
using States=std::unordered_map<Key,Path,Hash>;
struct Engine {
    std::vector<Ride> rides;
    std::vector<Walk> walks;
    std::vector<Pattern> patterns;
    std::vector<std::vector<int>> outgoing,foot;
    std::vector<unsigned char> output;
    double buffer;
    int origin=0;
    bool better(const Path&a,const Path&b)const{
        if(a.units!=b.units)return a.units<b.units;
        if(a.seconds!=b.seconds)return a.seconds<b.seconds;
        if(a.walking!=b.walking)return a.walking<b.walking;
        if(a.edges!=b.edges)return a.edges<b.edges;
        return a.walks<b.walks;
    }
    Key key(const Path&p,int stop,int pending=0)const{
        Key k;k.stop=stop;k.units=p.units;k.pending=pending;
        for(int i=0;i<p.length;i++)k.sequence[i]=p.patterns[i]+1;
        return k;
    }
    void keep(States& s,const Path&p,int pending=0){
        auto k=key(p,p.destination,pending);auto it=s.find(k);
        if(it==s.end())s.emplace(k,p);else if(better(p,it->second))it->second=p;
    }
    void offer(std::vector<Path>& bucket,const Path&p){
        if(p.destination==origin)return;
        for(auto &old:bucket){
            bool same=old.length==p.length;
            for(int i=0;same&&i<p.length;i++)same=patterns[old.patterns[i]].service==patterns[p.patterns[i]].service;
            if(same){if(better(p,old)){old=p;std::sort(bucket.begin(),bucket.end(),[&](auto&a,auto&b){return better(a,b);});}return;}
        }
        if(bucket.size()==5&&!better(p,bucket.back()))return;
        bucket.push_back(p);std::sort(bucket.begin(),bucket.end(),[&](auto&a,auto&b){return better(a,b);});
        if(bucket.size()>5)bucket.pop_back();
    }
    bool repeated(const Path&p,int pattern)const{
        for(int i=0;i<p.length;i++)if(patterns[p.patterns[i]].service==patterns[pattern].service)return true;
        return false;
    }
    void integer(uint32_t value){for(int i=0;i<4;i++)output.push_back((value>>(8*i))&255);}
    void generate(int start,int ceiling){
        origin=start;output.clear();
        std::vector<std::vector<Path>> answers(outgoing.size());
        States frontier;
        auto initial=[&](int stop,int walk,double seconds){
            for(int eid:outgoing[stop]){
                auto&e=rides[eid];Path p;p.edges[0]=eid;p.patterns[0]=e.pattern;p.length=1;p.destination=e.destination;
                p.walks[0]=walk;p.walking=seconds;p.seconds=seconds+e.seconds+patterns[e.pattern].wait;
                keep(frontier,p);
            }
        };
        initial(start,0,0);
        for(int wid:foot[start])if(walks[wid].internal)initial(walks[wid].destination,wid,walks[wid].seconds);
        for(int depth=0;!frontier.empty()&&depth<=ceiling;depth++){
            for(auto &item:frontier){
                const Path&p=item.second;
                offer(answers[p.destination],p);
                for(int wid:foot[p.destination]){
                    auto&w=walks[wid];Path q=p;q.destination=w.destination;q.seconds+=w.seconds;q.walking+=w.seconds;q.walks[4]=wid;
                    offer(answers[q.destination],q);
                }
            }
            if(depth==ceiling)break;
            States boarding,next;
            for(auto &item:frontier){
                const Path&p=item.second;if(p.units>=ceiling)continue;
                keep(boarding,p,1);
                for(int wid:foot[p.destination]){
                    auto&w=walks[wid];Path q=p;q.destination=w.destination;q.seconds+=w.seconds;q.walking+=w.seconds;
                    q.walks[q.length]=wid;keep(boarding,q,w.internal?1:0);
                }
            }
            for(auto&item:boarding){
                const Path&p=item.second;bool internal=item.first.pending;
                for(int eid:outgoing[p.destination]){
                    const Ride&e=rides[eid];if(repeated(p,e.pattern))continue;
                    int cost=internal&&patterns[p.patterns[p.length-1]].rail&&patterns[e.pattern].rail?1:3;
                    if(p.units+cost>ceiling||e.destination==start)continue;
                    Path q=p;q.edges[q.length]=eid;q.patterns[q.length]=e.pattern;q.length++;q.units+=cost;
                    q.destination=e.destination;q.seconds+=buffer+e.seconds+patterns[e.pattern].wait;
                    keep(next,q);
                }
            }
            frontier.swap(next);
        }
        for(uint32_t destination=0;destination<answers.size();destination++){
            auto&bucket=answers[destination];if(bucket.empty())continue;
            integer(destination);size_t length_pos=output.size();integer(0);size_t begin=output.size();
            output.push_back(bucket.size());
            for(auto&p:bucket){
                output.push_back(p.length);output.push_back(p.units);integer(p.walks[0]);
                for(int i=0;i<p.length;i++){integer(p.edges[i]);if(i)integer(p.walks[i]);}
                integer(p.walks[4]);
            }
            uint32_t length=output.size()-begin;
            for(int i=0;i<4;i++)output[length_pos+i]=(length>>(8*i))&255;
        }
    }
};
static thread_local std::string error;
extern "C" {
void* pap_engine(const Ride*r,int nr,const Walk*w,int nw,const Pattern*p,int np,int stops,double buffer){
    try{
        auto*e=new Engine;e->rides.assign(r,r+nr);e->walks.assign(w,w+nw);e->patterns.assign(p,p+np);
        e->outgoing.resize(stops);e->foot.resize(stops);e->buffer=buffer;
        for(int i=1;i<nr;i++)e->outgoing[e->rides[i].origin].push_back(i);
        for(int i=1;i<nw;i++)e->foot[e->walks[i].origin].push_back(i);
        return e;
    }catch(const std::exception&e){error=e.what();return nullptr;}
}
int pap_generate(void*ptr,int origin,int ceiling,const unsigned char**data,uint64_t*size){
    try{auto*e=static_cast<Engine*>(ptr);e->generate(origin,ceiling);*data=e->output.data();*size=e->output.size();return 0;}
    catch(const std::exception&e){error=e.what();return -1;}
}
const char* pap_error(){return error.c_str();}
void pap_free(void*ptr){delete static_cast<Engine*>(ptr);}
}
