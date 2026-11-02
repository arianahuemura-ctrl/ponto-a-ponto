// Read-only exhaustive directed-pair census. Each process owns disjoint origins.
// Minimal declarations for the installed SQLite C ABI (development headers absent).
extern "C" {
struct sqlite3; struct sqlite3_stmt;
int sqlite3_open_v2(const char*,sqlite3**,int,const char*);
int sqlite3_close(sqlite3*);
int sqlite3_exec(sqlite3*,const char*,int(*)(void*,int,char**,char**),void*,char**);
int sqlite3_prepare_v2(sqlite3*,const char*,int,sqlite3_stmt**,const char**);
int sqlite3_bind_int(sqlite3_stmt*,int,int);
int sqlite3_step(sqlite3_stmt*);
int sqlite3_column_int(sqlite3_stmt*,int);
const void* sqlite3_column_blob(sqlite3_stmt*,int);
int sqlite3_column_bytes(sqlite3_stmt*,int);
int sqlite3_reset(sqlite3_stmt*);
int sqlite3_clear_bindings(sqlite3_stmt*);
int sqlite3_finalize(sqlite3_stmt*);
}
constexpr int SQLITE_OPEN_READONLY=1,SQLITE_OK=0,SQLITE_ROW=100,SQLITE_DONE=101;
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <string>
#include <stdexcept>
int main(int argc,char**argv){
 if(argc!=6)return 2;
 sqlite3*db=nullptr;if(sqlite3_open_v2(argv[1],&db,SQLITE_OPEN_READONLY,nullptr)!=SQLITE_OK)return 3;
 sqlite3_exec(db,"PRAGMA cache_size=-4096",nullptr,nullptr,nullptr);
 int start=atoi(argv[2]),end=atoi(argv[3]),n=atoi(argv[4]);FILE*out=fopen(argv[5],"w");if(!out)return 4;
 std::vector<sqlite3_stmt*>q;
 for(auto table:{"paths","expanded_paths","topup_paths","short_walk_paths"}){
  std::string sql="SELECT destination,";sql+=(std::string(table)=="short_walk_paths"?"1":"substr(data,1,1)");sql+=" FROM "+std::string(table)+" WHERE origin=?";
  sqlite3_stmt*s;if(sqlite3_prepare_v2(db,sql.c_str(),-1,&s,nullptr)!=SQLITE_OK)return 5;q.push_back(s);
 }
 for(int a=start;a<end;a++){
  auto t=std::chrono::steady_clock::now();std::vector<unsigned char>counts(n,0);long long scanned=0;
  for(int k=0;k<4;k++){
   auto s=q[k];sqlite3_bind_int(s,1,a);int rc;
   while((rc=sqlite3_step(s))==SQLITE_ROW){int b=sqlite3_column_int(s,0);if(b<0||b>=n||b==a)return 6;
    if(k==3)counts[b]++;else{auto data=(const unsigned char*)sqlite3_column_blob(s,1);if(!data||sqlite3_column_bytes(s,1)!=1)return 7;counts[b]=data[0];}
    if(counts[b]>5||counts[b]<1)return 8;scanned++;
   }
   if(rc!=SQLITE_DONE)return 9;sqlite3_reset(s);sqlite3_clear_bindings(s);
  }
  long long hist[6]={};for(int b=0;b<n;b++)if(a!=b)hist[counts[b]]++;
  double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();
  fprintf(out,"{\"origin\":%d,\"histogram\":[%lld,%lld,%lld,%lld,%lld,%lld],\"rows_scanned\":%lld,\"seconds\":%.6f}\n",a,hist[0],hist[1],hist[2],hist[3],hist[4],hist[5],scanned,elapsed);fflush(out);
 }
 for(auto s:q)sqlite3_finalize(s);sqlite3_close(db);fclose(out);return 0;
}
