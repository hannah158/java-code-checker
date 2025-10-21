import streamlit as st
import json
import openai
import time
import random
import re
import streamlit_ace as st_ace

st.set_page_config(layout="wide", page_title="Java 体检室")
st.title("🎯 Java 代码AI检查小助手")

# CSS样式调整，支持全宽知识点框
st.markdown("""
<style>
.diagnosis{font-size:14px;white-space:pre-wrap;line-height:1.8;margin:0 0 0.8em 0;}
/* 知识点框：支持全宽，取消宽度限制 */
.knowledge-box{
    background-color:#f0f7ff;
    padding:15px;
    border-radius:8px;
    margin:10px 0;
    width: 100% !important;
    max-width: none !important;
    box-sizing: border-box;
}
.knowledge-title{font-weight:bold;color:#1a5fb4;margin-bottom:8px;}
/* 代码示例：适配全宽，长代码自动换行 */
.example-code{
    background-color:#f8f8f8;
    padding:8px;
    border-radius:4px;
    font-family:monospace;font-size:13px;
    width: 100% !important;
    box-sizing: border-box;
    white-space: pre-wrap;
}
/* 全宽区域容器：消除页面默认内边距 */
.full-width-container{
    padding: 0 10px;
    margin-top: 20px;
}
</style>""", unsafe_allow_html=True)

# 错误类型-内置知识点映射表（新增“参数类型不匹配”）
ERROR_KNOWLEDGE = {
    "数组越界": {
        "标题": "Java数组索引越界问题",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java数组的索引从0开始计数，长度为n的数组，有效索引范围是0~n-1。当访问的索引≥n或＜0时，会触发ArrayIndexOutOfBoundsException。

  <div class="knowledge-title">2. 避免方法</div>
  - 访问数组前，先确认数组长度：int len = arr.length;
  - 循环遍历数组时，用索引＜数组长度作为条件（如for(int i=0; i<arr.length; i++)）。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
int[] arr = {1,2,3}; // 长度为3，有效索引0、1、2
System.out.println(arr[3]); // 错误：索引3超出范围
  </div>
</div>
        """
    },
    "缺少分号": {
        "标题": "Java语句分号遗漏问题",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java要求每条语句必须以分号(;)结尾，分号是语句结束的标志。缺少分号会导致编译器无法识别语句边界，直接报错。

  <div class="knowledge-title">2. 避免方法</div>
  - 写完一条语句后立即添加分号（如int a=10;）；
  - 注意：代码块（{}中的内容）、循环条件、方法声明后不需要分号。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
int num = 10  // 错误：缺少分号
System.out.println(num); 
  </div>
</div>
        """
    },
    "关键字大小写错误": {
        "标题": "Java关键字大小写规范",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java是严格区分大小写的语言：
  - 关键字（如public、int、if）必须全小写；
  - 系统类（如System、String）必须首字母大写；
  大小写错误会导致编译器无法识别，视为语法错误。

  <div class="knowledge-title">2. 避免方法</div>
  - 记住常见关键字的正确拼写（全小写）；
  - 系统类名首字母大写（如System.out.println()）；
  - 使用IDE（如IDEA）的自动提示功能，减少手动输入错误。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
Public class Test { // 错误：public应为全小写
    INT a = 5; // 错误：int应为全小写
    system.out.println(a); // 错误：System应首字母大写
}
  </div>
</div>
        """
    },
    "数组初始化格式错误": {
        "标题": "Java数组初始化正确格式",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  数组初始化有严格格式要求，常见错误包括：
  - 同时指定长度和具体值（如new int[3]{1,2,3}）；
  - 错误使用圆括号()（应为花括号{}）；
  - 声明与初始化格式混乱（如int[] arr[] = {1,2,3}）。

  <div class="knowledge-title">2. 正确格式</div>
  <div class="example-code">
// 方式1：直接赋值（最常用）
int[] arr1 = {1,2,3};

// 方式2：指定长度（默认初始化）
int[] arr2 = new int[3];

// 方式3：完整格式（适合在方法参数中使用）
int[] arr3 = new int[]{1,2,3};
  </div>
</div>
        """
    },
    "变量未初始化": {
        "标题": "Java局部变量初始化要求",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java规定：方法内部的局部变量必须先初始化（赋值）才能使用。
  即使变量在逻辑上会被赋值（如if条件内），编译器也会视为“可能未初始化”而报错。

  <div class="knowledge-title">2. 避免方法</div>
  - 声明时直接初始化：int num = 0;
  - 确保所有分支都有赋值（如if-else都给变量赋值）。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
int num; // 仅声明未初始化
if (3>2) {
    num = 10; 
}
// 错误：编译器认为if条件可能不成立，num可能未赋值
System.out.println(num); 
  </div>
</div>
        """
    },
    "死循环": {
        "标题": "Java循环终止条件问题",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  死循环是指循环条件永远为true，导致循环无法结束。常见原因：
  - 循环变量未更新（如while循环中忘记i++）；
  - 终止条件设置错误（如i < 10写成i > 10）。

  <div class="knowledge-title">2. 避免方法</div>
  - 确保循环变量在每次循环中被更新（如i++、i -= 2）；
  - 测试时用小数据量验证，观察循环是否能正常结束。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
int i = 1;
while (i <= 5) { // 死循环：i始终为1，条件永远成立
    System.out.println(i);
    // 遗漏 i++
}
  </div>
</div>
        """
    },
    "for循环语法错误": {
        "标题": "Java for循环语法规范（含更新表达式检查）",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  for循环必须遵循“三部分”语法结构：for(初始化表达式; 条件表达式; 更新表达式)，三部分缺一不可：
  - 缺少分号：如for(int i=0; i<5{（条件后无分号）；
  - 缺少更新表达式：如for(int i=0; i<5;){（无i++等更新操作），会导致死循环；
  - 更新表达式无效：如for(int i=0; i<5; i=0){（循环变量未递增/递减）。

  <div class="knowledge-title">2. 正确格式</div>
  <div class="example-code">
// 标准结构：初始化（定义循环变量）; 条件（循环终止判断）; 更新（循环变量变化）
for (int i = 0; i < 5; i++) { // i++是更新表达式，确保i递增，循环能结束
    sum += i; 
}
  </div>

  <div class="knowledge-title">3. 常见错误案例</div>
  <div class="example-code">
// 错误1：缺少条件后的分号
for (int i = 0; i <5{ sum += i; }

// 错误2：缺少更新表达式（i不变化，条件i<5永远成立，死循环）
for (int i = 0; i <5;){ sum += i; }

// 错误3：更新表达式无效（i始终为0，死循环）
for (int i = 0; i <5; i=0){ sum += i; }
  </div>
</div>
        """
    },
    "System类大小写错误": {
        "标题": "Java System类大小写规范",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  System是Java的核心系统类（属于java.lang包），类名必须首字母大写。
  写成小写“system”会导致编译器无法识别，视为“找不到符号”错误。

  <div class="knowledge-title">2. 避免方法</div>
  - 记住System类的正确写法：首字母大写（S大写，其余小写）；
  - 常用方法：System.out.println()（打印输出）、System.currentTimeMillis()（获取时间）。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
int sum = 10;
system.out.println(sum); // 错误：system应为System（首字母大写）
System.out.println(sum); // 正确：首字母大写
  </div>
</div>
        """
    },
    "方法嵌套错误": {
        "标题": "Java方法嵌套不允许问题",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java不允许在一个方法内部定义另一个方法（即方法嵌套）。
  例如在main方法内部再定义main方法，会导致编译器无法识别方法边界，直接报错。

  <div class="knowledge-title">2. 避免方法</div>
  - 方法必须定义在类内部、其他方法外部；
  - 一个类中可以有多个方法，但方法之间不能嵌套。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
public class Test{
    public static void main(String[] args){
        // 错误：在main方法内部定义main方法（方法嵌套）
        public static void main(String[] args){ 
            int sum = 0;
        }
    }
}
  </div>
</div>
        """
    },
    "多余大括号错误": {
        "标题": "Java代码块大括号匹配规范",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java中每个代码块（类体、方法体、循环体）的大括号必须成对出现，多余的右大括号（}）会导致编译器认为“代码结构不完整”，直接报错。

  <div class="knowledge-title">2. 避免方法</div>
  - 写代码时遵循“先写大括号再填内容”的习惯（如class Test{}）；
  - 缩进对齐：通过缩进确认大括号的对应关系（如类体、方法体的大括号各占一行，缩进一致）。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
public class Test{
    public static void main(String[] args){
        int sum = 0;
    }
    }
} // 错误：多余的右大括号（类体只需1对大括号）
  </div>
</div>
        """
    },
    # 新增：参数类型不匹配知识点
    "参数类型不匹配": {
        "标题": "Java方法参数类型匹配规则",
        "内容": """
<div class="knowledge-box">
  <div class="knowledge-title">1. 错误原因</div>
  Java是强类型语言，调用方法时传入的参数类型必须与方法声明的参数类型严格匹配：
  - 基本类型（如int、double）不能直接传入字符串（如"20"）；
  - 引用类型（如String、数组）必须与声明类型一致或为其子类（多态场景）。

  <div class="knowledge-title">2. 避免方法</div>
  - 调用前检查方法声明的参数类型（如`printSum(int a, int b)`需传入两个int值）；
  - 如需转换类型，使用包装类方法（如`Integer.parseInt("20")`将字符串转为int）。

  <div class="knowledge-title">3. 常见案例</div>
  <div class="example-code">
// 方法声明：需要两个int类型参数
public static void printSum(int a, int b) { ... }

// 错误调用：第二个参数是String类型（"20"），与int不匹配
printSum(10, "20"); 

// 正确调用：将字符串转为int类型
printSum(10, Integer.parseInt("20")); 
  </div>
</div>
        """
    }
}


# 错误类型识别函数（新增“参数类型不匹配”识别关键词）
def extract_error_types(error_desc):
    if not error_desc or error_desc == "无":
        return []
    error_keywords = {
        "数组越界": ["数组越界", "索引超出", "ArrayIndexOutOfBounds", "数组索引越界", "超出数组长度", "索引无效"],
        "缺少分号": ["缺少分号", "语句结尾无分号"],
        "关键字大小写错误": ["关键字大小写", "INT", "Public", "If"],
        "数组初始化格式错误": ["数组初始化", "new int[3]{", "int[] arr[]"],
        "变量未初始化": ["变量未初始化", "可能未赋值"],
        "死循环": ["死循环", "循环条件永远为true", "未更新循环变量"],
        "for循环语法错误": [
            "for循环语法", "缺少分号",
            "缺少更新表达式", "无更新操作",
            "i++", "i--", "循环变量未递增", "循环变量未递减"
        ],
        "System类大小写错误": ["system", "System类大小写"],
        "方法嵌套错误": ["方法嵌套", "内部定义方法"],
        "多余大括号错误": ["多余大括号", "右大括号过多"],
        # 新增：参数类型不匹配的识别关键词
        "参数类型不匹配": ["参数类型不匹配", "类型错误", "无法应用于给定类型", "incompatible types", "argument mismatch"]
    }
    matched_types = []
    for error_type, keywords in error_keywords.items():
        if any(keyword in error_desc for keyword in keywords):
            matched_types.append(error_type)
    return list(set(matched_types))


# 提示词优化（新增方法参数匹配检查）
api_key = "sk-0NYD4qPzaZ2HUC8GuXBcRDhGExFQYed9iZHmSYryj399nYnl"
client = openai.OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")

SYSTEM = """你是《Java程序设计》专属助教，必须逐行、精准检查代码，重点识别for循环和方法参数的所有错误，不遗漏逻辑问题。
输入格式：每行前面带有 [行号] 标记，例如 [3] int sum=0;
### 强制检查清单（for循环和方法参数为重点检查项，必须覆盖以下所有子项）
1. for循环三部分完整性检查（缺一不可）：
   - 初始化表达式：是否定义循环变量（如int i=0）；
   - 条件表达式：是否有循环终止判断（如i<5）；
   - **更新表达式：是否有循环变量更新操作（如i++、i--、i+=2），无更新操作则判定为错误（会导致死循环）**；
   - 分号检查：三部分之间是否用分号分隔（如for(;;)中缺少分号则为错误）。

2. 方法参数匹配检查（新增）：
   - 检查传入参数类型与方法声明的参数类型是否一致（如int参数传入String）；
   - 若不匹配，需明确标注“参数类型不匹配”，并说明期望类型与实际传入类型（如“期望int，实际传入String”）。

3. 其他必查项：
   - 关键字大小写：仅检查全大写关键字（INT、Public），正确全小写（public、int）禁止误判；
   - 系统类大小写：仅检查全小写系统类（system），正确首字母大写（System）禁止误判；
   - 方法嵌套：检查是否在方法内定义方法（如main内写main）；
   - 大括号匹配：检查是否有多余右大括号；
   - 方法调用：仅检查括号不匹配，括号完整禁止误判。

### 规则（必须遵守）
1. 发现for循环无更新表达式时，必须标注为“for循环语法错误”，错误描述需包含“缺少更新表达式”“会导致死循环”；
2. 发现参数类型不匹配时，必须标注为“参数类型不匹配”，错误描述需包含“期望类型”和“实际传入类型”；
3. 每个错误需对应输入中的行号，禁止虚构错误，禁止误判正确代码；
4. 输出JSON中的“逻辑错误”需包含for循环死循环风险和参数类型不匹配的影响（如“[8]：参数类型不匹配会导致编译失败”）。

### 输出JSON格式（严格遵守）
{
  "编译错误":"[行号]：错误详情（例：[6]：for循环语法错误，缺少条件后的分号；[8]：参数类型不匹配，期望int，实际传入String），无错误则填“无”",
  "逻辑错误":"[行号]：错误详情（例：[6]：for循环缺少更新表达式，i不递增会导致死循环；[8]：参数类型不匹配会导致编译失败），无错误则填“无”",
  "风格问题":"[行号]：问题详情（仅填真实存在的问题，无则填“无”）",
  "改进建议":"1. [行号]：具体改进操作（例：1. [6]：在for循环条件后添加分号；2. [8]：将\"20\"转为int类型：Integer.parseInt(\"20\")）\n2. ... 无建议则填“无”",
  "重写代码":"已修正所有错误的完整Java代码（不带行号，格式规范），无错误则保留原代码"
}"""

with st.sidebar:
    st.subheader("① 写/贴代码")
    # 示例代码包含参数类型不匹配错误，方便测试新增功能
    raw_code = st_ace.st_ace(
        value="public class Demo {\n    public static void printSum(int a, int b) {\n        System.out.println(a + b);\n    }\n\n    public static void main(String[] args) {\n        printSum(10, \"20\"); // ❌ 错误：参数类型不匹配\n    }\n}",
        language="java", theme="monokai", show_gutter=True, height=380, tab_size=4)

code_lines = raw_code.strip('\n').splitlines()
injected = '\n'.join(f"[{idx + 1}] {line}" for idx, line in enumerate(code_lines))


def ask_kimi(code: str):
    max_retry = 3
    for attempt in range(1, max_retry + 1):
        try:
            rsp = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": f"请重点检查for循环的更新表达式和方法参数类型匹配，逐行精准检查以下Java代码：\n{code}"}],
                temperature=0.05,
                response_format={"type": "json_object"}
            )
            raw = rsp.choices[0].message.content
            clean = re.sub(r'[\x00-\x1F\x7F]', '', raw).strip()
            if clean.startswith('{') and clean.endswith('}'):
                return json.loads(clean, strict=False)
            else:
                json_match = re.search(r'\{[\s\S]*\}', clean)
                if json_match:
                    return json.loads(json_match.group(), strict=False)
                else:
                    raise ValueError("AI输出未包含有效JSON")
        except openai.RateLimitError:
            wait = 2 ** attempt + random.uniform(0, 1)
            if attempt == max_retry:
                raise RuntimeError("Kimi 引擎繁忙，请稍后再试！") from None
            st.warning(f"引擎过载，{wait:.1f} 秒后重试（{attempt}/{max_retry}）...")
            time.sleep(wait)
        except Exception as e:
            raise e


# 按钮点击逻辑
if st.sidebar.button("生成反馈", type="primary"):
    if not api_key:
        st.error("请先填 KEY")
        st.stop()

    out = {
        "编译错误": "无",
        "逻辑错误": "无",
        "风格问题": "无",
        "改进建议": "无",
        "重写代码": raw_code
    }

    with st.spinner("等待 Kimi …"):
        try:
            result = ask_kimi(injected)
            for key in out.keys():
                if key in result and result[key] != "":
                    out[key] = result[key]
        except Exception as e:
            st.exception(e)

    # 分项诊断与修正后代码
    col_feed, col_code = st.columns([1, 1])
    with col_feed:
        st.subheader("📋 分项诊断")
        icons = {"编译错误": "📄", "逻辑错误": "🧠", "风格问题": "✨"}
        for title in ["编译错误", "逻辑错误", "风格问题"]:
            st.markdown(f'{icons[title]} **{title}**')
            st.markdown(f'<div class="diagnosis">{out[title]}</div>', unsafe_allow_html=True)

        st.markdown("🔧 **改进建议**")
        st.markdown(f'<div class="diagnosis">{out["改进建议"]}</div>', unsafe_allow_html=True)

    with col_code:
        st.subheader("🔧 修正后代码")
        fixed_code = out["重写代码"].replace('\\n', '\n').replace('\\t', '\t')
        st.code(fixed_code, language="java")

    # 相关知识点讲解（全宽显示）
    st.markdown('<div class="full-width-container">', unsafe_allow_html=True)
    st.subheader("📚 相关知识点讲解")
    all_errors = out["编译错误"] + " " + out["逻辑错误"]
    matched_error_types = extract_error_types(all_errors)

    if matched_error_types:
        for error_type in matched_error_types:
            st.markdown(f'### {ERROR_KNOWLEDGE[error_type]["标题"]}', unsafe_allow_html=True)
            st.markdown(ERROR_KNOWLEDGE[error_type]["内容"], unsafe_allow_html=True)
    else:
        st.markdown('<div class="diagnosis">代码无明显错误，可尝试学习Java基础语法哦～</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
