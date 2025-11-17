import streamlit as st
import json
import openai
import time
import re
import streamlit_ace as st_ace
import os
from dotenv import load_dotenv

st.set_page_config(layout="wide", page_title="JavaWeb 体检室")
st.title("🎯 JavaWeb代码AI检查小助手")
st.markdown("⚠️ **检测5类最常见错误**：Servlet映射、路径斜杠、异常声明、中文乱码、JSP标签")

# CSS样式（优化知识点显示）
st.markdown("""
<style>
.error-item{margin:8px 0;padding:10px;border-left:3px solid #ff4b4b;background:#fff5f5;}
.knowledge{background:#f0f7ff;padding:15px;border-radius:6px;margin:15px 0;}
.knowledge-title{font-weight:bold;color:#1a5fb4;font-size:16px;margin-bottom:8px;}
.knowledge-content{font-size:14px;line-height:1.6;}
</style>""", unsafe_allow_html=True)

# 5类错误的知识点（结构更清晰）
ERROR_KNOWLEDGE = {
    "缺少@WebServlet注解": {
        "title": "Servlet必须添加@WebServlet注解",
        "content": """
<div class="knowledge-content">
  <strong>为什么错？</strong>：Servlet需要告诉服务器“通过哪个URL能访问它”，没加@WebServlet注解的话，服务器找不到这个Servlet，访问时会报404错误。<br><br>
  <strong>怎么改？</strong>：在Servlet类的上面添加注解，路径必须以/开头，例如：<br>
  <code>@WebServlet("/student/list")</code><br><br>
  <strong>例子</strong>：<br>
  <code>@WebServlet("/hello")</code><br>
  <code>public class HelloServlet extends HttpServlet { ... }</code>
</div>
        """
    },
    "@WebServlet路径缺少斜杠": {
        "title": "@WebServlet的路径必须以/开头",
        "content": """
<div class="knowledge-content">
  <strong>为什么错？</strong>：Servlet的访问路径必须以/开头（比如"/login"），如果写成"login"（没加/），服务器会认为这是一个相对路径，无法正确识别，导致404错误。<br><br>
  <strong>怎么改？</strong>：在路径前面加/，例如：<br>
  错误：<code>@WebServlet("student/list")</code><br>
  正确：<code>@WebServlet("/student/list")</code>
</div>
        """
    },
    "doGet/doPost缺少异常声明": {
        "title": "doGet/doPost必须声明throws异常",
        "content": """
<div class="knowledge-content">
  <strong>为什么错？</strong>：HttpServlet类中的doGet/doPost方法本身声明了会抛出<code>ServletException</code>和<code>IOException</code>，子类重写时必须“继承”这个声明，否则编译会报错。<br><br>
  <strong>怎么改？</strong>：在方法后面加上异常声明，例如：<br>
  <code>protected void doGet(HttpServletRequest request, HttpServletResponse response) 
          throws ServletException, IOException { ... }</code>
</div>
        """
    },
    "响应未设置UTF-8字符集": {
        "title": "必须设置UTF-8避免中文乱码",
        "content": """
<div class="knowledge-content">
  <strong>为什么错？</strong>：如果只写<code>response.setContentType("text/html")</code>，服务器会用默认编码（可能不是UTF-8）返回内容，导致页面上的中文显示为???或乱码。<br><br>
  <strong>怎么改？</strong>：在contentType中明确指定字符集，例如：<br>
  <code>response.setContentType("text/html;charset=UTF-8");</code>
</div>
        """
    },
    "JSP标签错误": {
        "title": "JSP标签必须正确闭合和使用",
        "content": """
<div class="knowledge-content">
  <strong>为什么错？</strong>：<br>
  1. JSP的<code><%</code>标签必须用<code>%></code>闭合，否则会导致编译错误；<br>
  2. 输出变量应该用<code><%= 变量 %></code>（自动打印），而不是用<code><% out.print(变量); %></code>（麻烦且容易错）。<br><br>
  <strong>怎么改？</strong>：<br>
  输出变量：<code><%= username %></code>（正确）<br>
  代码块：<code><% if (age > 18) { %> 成年 <% } %></code>（必须用%>闭合）
</div>
        """
    }
}


# 错误识别函数（确保精准匹配）
def extract_errors(error_desc):
    if not error_desc or error_desc.strip() == "无":
        return []
    # 关键词与错误类型的映射（更精准）
    error_mapping = {
        "缺少@WebServlet注解": [
            "缺少@WebServlet", "没有@WebServlet", "Servlet无访问路径", "未添加@WebServlet注解"
        ],
        "@WebServlet路径缺少斜杠": [
            "路径缺少斜杠", "urlPatterns无斜杠", "@WebServlet路径没加/", "路径应为/开头"
        ],
        "doGet/doPost缺少异常声明": [
            "缺少throws", "未声明ServletException", "doGet缺少异常", "doPost未抛异常"
        ],
        "响应未设置UTF-8字符集": [
            "缺少charset=UTF-8", "中文乱码", "setContentType无UTF-8", "未设置字符集"
        ],
        "JSP标签错误": [
            "<%未闭合", "<%缺少%>", "用<% %>输出变量", "JSP标签错误"
        ]
    }
    matched_errors = []
    for err_type, keywords in error_mapping.items():
        for keyword in keywords:
            if keyword in error_desc:
                matched_errors.append(err_type)
                break  # 每个错误类型只加一次
    return list(set(matched_errors))  # 去重


# 环境配置
load_dotenv()
api_key = os.getenv("MOONSHOT_API_KEY")
if not api_key:
    st.error("请在.env文件中配置MOONSHOT_API_KEY")
    st.stop()
client = openai.OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")


# 提示词（强制返回可匹配的错误描述）
SYSTEM = """你是JavaWeb助教，**只检查并返回以下5类错误**，其他错误完全忽略：

1. 【缺少@WebServlet注解】：Servlet类没有@WebServlet(...)注解（例如：public class XxxServlet extends HttpServlet { ... } 上面没有@WebServlet）
2. 【@WebServlet路径缺少斜杠】：@WebServlet的urlPatterns路径没加/（例如：@WebServlet("login") 应为 @WebServlet("/login")）
3. 【doGet/doPost缺少异常声明】：doGet/doPost方法没写throws ServletException, IOException（例如：protected void doGet(...) { ... } 漏了异常声明）
4. 【响应未设置UTF-8字符集】：response.setContentType只写了"text/html"，没加;charset=UTF-8（例如：response.setContentType("text/html"); 应为 ..."text/html;charset=UTF-8"）
5. 【JSP标签错误】：JSP中<%没闭合%>，或用<% %>输出变量（应使用<%= %>）（例如：<% out.print(name); 或 <% ... 没写%>）

### 输出要求：
- 错误描述必须包含上方【】中的错误类型名称（方便匹配知识点）
- 每个错误标出行号，格式："1. [行号]【错误类型】：具体描述"
- 重写代码只修正这5类错误，保留原逻辑
- 严格返回JSON：{"错误列表":"...", "改进建议":"...", "重写代码":"..."}
"""


# 默认代码（包含5类错误，方便测试）
with st.sidebar:
    st.subheader("输入代码（Servlet/JSP）")
    raw_code = st_ace.st_ace(
        value="""// 包含5类初学者常见错误
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.PrintWriter;

// 错误1：缺少@WebServlet注解
public class StudentServlet extends HttpServlet {
    // 错误2：doGet缺少异常声明（漏throws ServletException, IOException）
    protected void doGet(HttpServletRequest request, HttpServletResponse response) {
        // 错误3：未设置UTF-8字符集（中文会乱码）
        response.setContentType("text/html");
        PrintWriter out = response.getWriter();
        out.println("学生列表：张三");
    }
}

// 错误4：@WebServlet路径缺少斜杠（应为"/teacher/list"）
@WebServlet("teacher/list")
public class TeacherServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException { // 错误5：漏了ServletException异常
        resp.setContentType("text/html"); // 错误6：未设置UTF-8
    }
}

// JSP错误示例
/*
<% 
    String name = "李四";
    out.print(name); // 错误7：应使用<%= name %>
%  // 错误8：标签未闭合（少了>）
*/
""",
        language="java", theme="monokai", height=400, tab_size=4)

code_lines = raw_code.strip('\n').splitlines()
injected = '\n'.join(f"[{idx+1}] {line}" for idx, line in enumerate(code_lines))


# AI调用函数
def check_code(code):
    for attempt in range(3):
        try:
            rsp = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"检查以下代码中的5类错误，按要求输出：\n{code}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(rsp.choices[0].message.content)
        except Exception as e:
            if attempt == 2:
                st.error(f"检查失败：{str(e)}")
                return None
            time.sleep(1)


# 核心逻辑（确保知识点一定显示）
if st.sidebar.button("检查常见错误", type="primary"):
    with st.spinner("正在检查5类常见错误..."):
        result = check_code(injected)
        if not result:
            st.stop()

    # 1. 展示错误列表
    st.subheader("🔍 发现的错误")
    error_list = result.get("错误列表", "无")
    if error_list == "无":
        st.success("未检测到这5类常见错误！代码在基础规范上没问题～")
    else:
        errors = re.split(r'\d+\.', error_list)
        for err in errors:
            err = err.strip()
            if err:
                st.markdown(f'<div class="error-item">{err}</div>', unsafe_allow_html=True)

    # 2. 展示改进建议
    st.subheader("✏️ 改进建议")
    st.markdown(f'<div>{result.get("改进建议", "无")}</div>', unsafe_allow_html=True)

    # 3. 展示修正后代码
    st.subheader("✅ 修正后代码")
    st.code(result.get("重写代码", raw_code), language="java")

    # 4. 展示知识点讲解（确保匹配并显示）
    st.subheader("📚 相关错误知识点讲解")
    matched_errors = extract_errors(error_list)
    if matched_errors:
        for err_type in matched_errors:
            # 确保错误类型在知识点表中
            if err_type in ERROR_KNOWLEDGE:
                st.markdown(f'<div class="knowledge-title">{ERROR_KNOWLEDGE[err_type]["title"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="knowledge">{ERROR_KNOWLEDGE[err_type]["content"]}</div>', unsafe_allow_html=True)
    else:
        if error_list == "无":
            st.info("代码未出现这5类常见错误，可继续学习其他JavaWeb知识～")
        else:
            st.warning("未找到对应知识点（可能是错误描述不匹配）")