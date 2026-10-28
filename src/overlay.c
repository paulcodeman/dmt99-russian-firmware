/* DMT-99 V2.4 UI-only Russian overlay. No storage, ASIC, or power writes.
 * Chinese language slot 0 becomes Russian; English slot 1 delegates to stock.
 * Original rendering functions remain callable through four-byte trampolines.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long uptr;
#include "font.h"

#define STOCK(addr, type) ((type)(uptr)(addr))
static unsigned russian(void) { return (*(volatile u16 *)0x2000003e & 7u) == 0; }
static void pixel(unsigned x,unsigned y,unsigned c) {
    if (x<320 && y<240) STOCK(0x7f00,void(*)(u32,u32,u32))(x,y,c);
}
static void fill(unsigned x,unsigned y,unsigned x1,unsigned y1,unsigned c) {
    if(x>319 || y>239 || x>x1 || y>y1)return;
    if(x1>319)x1=319;
    if(y1>239)y1=239;
    STOCK(0x8a02,void(*)(u32,u32,u32,u32,u32))(x,y,x1,y1,c);
}
static void line(unsigned x,unsigned y,unsigned x1,unsigned y1,unsigned c) {
    STOCK(0x8050,void(*)(u32,u32,u32,u32,u32))(x,y,x1,y1,c);
}
static unsigned length(const char *s) { unsigned n=0;while(*s){if(((u8)*s&0xc0)!=0x80)n++;s++;}return n; }
static unsigned equal(const char *a,const char *b) { while(*a && *a==*b){a++;b++;}return *a==*b; }
static char lower(char c){return c>='A'&&c<='Z'?c+32:c;}
static unsigned iequal(const char *a,const char *b){while(*a&&lower(*a)==lower(*b)){a++;b++;}return lower(*a)==lower(*b);}
static unsigned prefix(const char *a,const char *b){while(*b){if(lower(*a++)!=lower(*b++))return 0;}return 1;}
static unsigned contains(const char *s,const char *needle){for(;*s;s++)if(prefix(s,needle))return 1;return 0;}

/* Fixed 8x16 glyphs, clipped and scaled inside the caller's allocated region.
 * No font/filesystem dependency on the external resource partition. */
void ru_text(unsigned x,unsigned y,const char *s,unsigned height,unsigned width,unsigned color) {
    unsigned n=length(s),advance=height/2;
    if(!n || !width)return;
    if(n*advance>width)advance=width/n;
    if(!advance)return;
    unsigned glyph_width=advance;
    for(;*s;s++){
        unsigned cp=(u8)*s;
        if((cp&0xe0)==0xc0 && s[1]){cp=((cp&31)<<6)|((u8)*++s&63);}
        unsigned index=FONT_COUNT;
        for(unsigned i=0;i<FONT_COUNT;i++)if(ru_codepoints[i]==cp){index=i;break;}
        if(index<FONT_COUNT)for(unsigned yy=0;yy<height;yy++){
            unsigned bits=ru_font[index][yy*16/height];
            for(unsigned xx=0;xx<glyph_width;xx++)
                if(bits&(0x80u>>(xx*8/glyph_width)))pixel(x+xx,y+yy,color);
        }
        x+=advance;
    }
}

extern void original_string(u32,u32,const u8*,u32,u32,u32,u32);
extern void original_glyph12(u32,u32,const u8*,u32,u32,u32,u32);
extern void original_glyph16(u32,u32,const u8*,u32,u32,u32,u32);
extern void original_glyph24(u32,u32,const u8*,u32,u32,u32,u32);
extern void original_glyph32(u32,u32,const u8*,u32,u32,u32,u32);
extern void original_ascii_char(u32,u32,u32,u32,u32,u32,u32);
extern u32 original_image(const char*,u32,u32);
extern void original_compact(u32,u32,u32);
extern void original_large(u32,u32,u32);

static const char *translation(const u8 *s) {
    for(unsigned i=0;i<TRANSLATION_COUNT;i++)if(equal((const char*)s,ru_translations[i].gbk))return ru_translations[i].ru;
    return (const char*)0;
}
void hook_string(u32 x,u32 y,const u8 *s,u32 fg,u32 bg,u32 size,u32 transparent) {
    /* The first language option is labelled Russian even while English is
     * active. Its original GBK label means Simplified Chinese. */
    const char *t=(russian() || equal((const char*)s,"\xbc\xf2\xcc\xe5"))?translation(s):(const char*)0;
    if(!t){original_string(x,y,s,fg,bg,size,transparent);return;}
    unsigned width=x<130?128-x:310-x;
    unsigned h=size>16?20:size;
    if(x>=320 || y>=240)return;
    /* These stock labels sit next to a checkbox or another text column. */
    if(x==159 && y==12)width=70;
    if(x==169 && y==26)width=68;
    if(x==245 && y==26)width=68;
    if(x==191)width=117;
    if(x==157 && (y==87 || y==112))width=140;
    if(size==12 && x<210)width=75;
    if(!transparent)fill(x,y,x+width-1,y+size-1,bg);
    ru_text(x,y,t,h,width,fg);
}
/* Isolated glyphs are retained for physical unit signs and the warning icon.
 * Whole Chinese words go through hook_string; category columns are replaced
 * as complete rows, avoiding one-character-at-a-time Cyrillic substitution. */
void hook_glyph12(u32 x,u32 y,const u8*s,u32 a,u32 b,u32 c,u32 d){original_glyph12(x,y,s,a,b,c,d);}
void hook_glyph16(u32 x,u32 y,const u8*s,u32 a,u32 b,u32 c,u32 d){original_glyph16(x,y,s,a,b,c,d);}
void hook_glyph24(u32 x,u32 y,const u8*s,u32 a,u32 b,u32 c,u32 d){original_glyph24(x,y,s,a,b,c,d);}
void hook_glyph32(u32 x,u32 y,const u8*s,u32 a,u32 b,u32 c,u32 d){original_glyph32(x,y,s,a,b,c,d);}

void hook_ascii_char(u32 x,u32 y,u32 ch,u32 size,u32 fg,u32 bg,u32 transparent) {
    /* Stock colons are positioned for two Chinese characters. Russian labels
     * use the full heading width, so suppress only these decorative colons. */
    if(russian() && ch==':' && ((x==201&&(y==23||y==86||y==152)) ||
       (x==172&&(y==5||y==82||y==160)) || (x==184&&(y==9||y==125)) ||
       (x==231&&(y==9||y==125))))return;
    original_ascii_char(x,y,ch,size,fg,bg,transparent);
}

static void category(unsigned large,unsigned initial,unsigned selected,unsigned previous) {
    static const char *const labels[]={"Режим","Пороги","История","Настройки","Сброс","О приборе"};
    static const u16 tops[]={29,61,91,122,152,183},bottoms[]={59,89,120,150,181,210};
    if(initial){
        for(unsigned i=0;i<6;i++){
            if(i)line(0,large?39*i:(unsigned)tops[i]-1,large?129:119,large?39*i:(unsigned)tops[i]-1,0x4228);
            ru_text(large?5:4,large?10+39*i:35+(i*61)/2,labels[i],large?20:16,large?120:112,0xffff);
        }
        line(large?130:120,large?0:29,large?130:120,large?234:210,0x4228);
    }
    if(selected>=1 && selected<=6){
        unsigned i=selected-1,y=large?39*i+1:tops[i],end=large?39*(i+1)-2:bottoms[i];
        fill(0,y,large?128:119,end,large?0xfd40:0x1c9f);
        ru_text(large?5:4,large?10+39*i:35+(i*61)/2,labels[i],large?20:16,large?120:112,0);
    }
    if(previous>=1 && previous<=6 && previous!=selected){
        unsigned i=previous-1,y=large?39*i+1:tops[i],end=large?39*(i+1)-2:bottoms[i];
        fill(0,y,large?128:119,end,0);
        ru_text(large?5:4,large?10+39*i:35+(i*61)/2,labels[i],large?20:16,large?120:112,0xffff);
    }
}
void hook_compact(u32 initial,u32 selected,u32 previous){if(russian())category(0,initial,selected,previous);else original_compact(initial,selected,previous);}
void hook_large(u32 initial,u32 selected,u32 previous){if(russian())category(1,initial,selected,previous);else original_large(initial,selected,previous);}

static void box(unsigned x,unsigned y,unsigned w,unsigned h,const char *s,unsigned color) {
    fill(x,y,x+w-1,y+h-1,0);
    ru_text(x+2,y+(h>16?(h-16)/2:0),s,h<16?h:16,w>4?w-4:w,color);
}
u32 hook_image(const char *path,u32 x,u32 y) {
    if(!russian())return original_image(path,x,y);
    const char *s=path;if(s[0]&&s[1]==':')s+=s[2]=='/'?3:2;
    const unsigned yellow=0xfd40,white=0xffff,red=0xf800;
    if(prefix(s,"menu/chinese/")){
        const char *name=s+13;
        if(iequal(name,"lan.jpg"))box(x,y,171,20,"Язык",white);
        else if(iequal(name,"light.jpg"))box(x,y,171,20,"Яркость",white);
        else if(iequal(name,"poweroff.jpg"))box(x,y,171,20,"Автовыключение",white);
        else if(iequal(name,"tem_unit.jpg"))box(x,y,171,20,"Единица темп.",white);
        else if(iequal(name,"mode3_value.jpg"))box(x,y,302,30,"ПОРОГ",yellow);
        else if(iequal(name,"recharge1.jpg")){
            fill(x,y,319,y+65,0);ru_text(x+12,y+4,"Не измеряйте при зарядке!",16,296,red);
            ru_text(x+12,y+26,"Для работы отключите USB.",16,296,red);
        }else if(iequal(name,"close.jpg")){
            fill(x,y,x+238,y+112,0);fill(x,y,x+238,y+26,red);
            ru_text(x+8,y+5,"Низкий заряд!",16,222,0);
            ru_text(x+8,y+36,"Прибор выключится",16,222,red);
            ru_text(x+8,y+57,"автоматически.",16,222,red);
        }else if(iequal(name,"recover1.jpg")){
            fill(x,y,x+188,y+239,0);fill(x+10,y+24,x+177,y+54,yellow);
            ru_text(x+18,y+30,"Внимание!",18,152,0);
            ru_text(x+14,y+76,"Сброс всех",18,162,yellow);
            ru_text(x+14,y+102,"настроек.",18,162,yellow);
            box(x+12,y+148,166,29,"Сбросить",white);box(x+12,y+188,166,29,"Назад",white);
        }else if(iequal(name,"recover1_1.jpg")||iequal(name,"recover1_2.jpg")){
            /* Stock state 30/recover1_1 selects Return; state 31 selects Reset. */
            unsigned pick=iequal(name,"recover1_2.jpg");
            box(x,y,166,29,"Сбросить",pick?yellow:white);box(x,y+40,166,29,"Назад",pick?white:yellow);
        }else return original_image(path,x,y);
        return 0;
    }
    if(iequal(s,"menu/about.jpg")){
        u32 result=original_image(path,x,y);
        fill(x,y+44,x+188,y+61,0);
        ru_text(x+2,y+45,"Производитель FNIRSI",14,184,white);
        return result;
    }
    /* Measurement/history labels containing Chinese are rendered into their
     * original boxes. DC/AC and physical unit symbols remain internationally
     * recognizable, and the numeric renderer is never intercepted. */
    if((prefix(s,"mode/")||prefix(s,"history/"))&&contains(s,"_c.jpg")){
        const char *label="";unsigned vertical=contains(s,"mode2_")&&!contains(s,"mode2_max");
        if(iequal(s,"mode/ac_dc_v_c.jpg"))label="Напряж.";
        else if(iequal(s,"mode/a-_c.jpg"))label="Малый ток";
        else if(iequal(s,"mode/a_c.jpg"))label="Большой ток";
        else if(contains(s,"ac_v")||contains(s,"~v"))label="AC V";
        else if(contains(s,"dc_v")||contains(s,"_v"))label="DC V";
        else if(contains(s,"ac_a")||contains(s,"~a"))label="AC A";
        else if(contains(s,"dc_a")||contains(s,"_a"))label="DC A";
        else if(contains(s,"cap"))label="Ёмкость";
        else if(contains(s,"temp")||contains(s,"tem_"))label="Темп.";
        else if(contains(s,"hz"))label="Частота";
        else if(contains(s,"res")||contains(s,"/r_"))label="Ом";
        else if(contains(s,"ol"))label="Диод/прозв.";
        else if(contains(s,"v_"))label="V";
        else if(contains(s,"a_"))label="A";
        if(contains(s,"mode2_max")){
            fill(x,y,x+203,y+17,0);
            ru_text(x,y+1,"МИН",12,26,0x07e0);
            ru_text(x+104,y+1,"МАКС",12,28,red);return 0;
        }
        if(vertical){
            fill(x,y,x+19,y+125,0);
            /* A compact vertical abbreviation fits the stock recording strip. */
            const char *v=contains(s,"cap")?"C":contains(s,"tem_")?"T":contains(s,"hz")?"Hz":contains(s,"r_")?"R":contains(s,"ol")?"Диод":contains(s,"v_")?"V":"A";
            if(contains(s,"dc_")){ru_text(x+1,y+12,"DC",12,18,white);}
            else if(contains(s,"ac_")){ru_text(x+1,y+12,"AC",12,18,white);}
            if(contains(s,"ol")){
                static const char *const chars[]={"Д","и","о","д"};
                for(unsigned i=0;i<4;i++)ru_text(x+4,y+20+i*20,chars[i],16,12,yellow);
            }else ru_text(x+2,y+38,v,16,18,yellow);
            return 0;
        }
        unsigned w=107,h=22;
        for(unsigned i=0;i<IMAGE_COUNT;i++)if(iequal(s,ru_images[i].path)){w=ru_images[i].w;h=ru_images[i].h;break;}
        if(prefix(s,"history/")&&contains(s,"cap"))label="Ёмк.";
        if(prefix(s,"history/")&&contains(s,"hz"))label="Гц";
        if(prefix(s,"history/")&&contains(s,"temp"))label="Темп";
        box(x,y,w,h,label,prefix(s,"mode/")?yellow:white);return 0;
    }
    return original_image(path,x,y);
}
