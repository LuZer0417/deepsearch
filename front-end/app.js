const { createApp } = Vue

createApp({
    data() {
        return {
            title: 'DeepSearch',
            searchQuery: '',
            searchType: 'or',  // 默认使用 OR 搜索
            allResults: [],      // 存储所有搜索结果
            currentResults: [],  // 当前页显示的结果
            searched: false,   // 是否已搜索
            loading: false,    // 是否正在加载
            currentPage: 1,      // 当前页码
            pageSize: 15,        // 每页显示数量
            totalResults: 0,   // 结果总数
            apiUrl: `http://${window.location.hostname}:${window.location.port}/api/search`,
            isDarkMode: false,  // Add dark mode state
            showAiResponse: false,
            aiResponse: "",
            isAiLoading: false,
            eventSource: null,
            aiSearchEnabled: true, // 默认启用AI搜索
            md: null,
            lastSearchQuery: '', // 上次搜索的查询
            suggestions: [],     // 查询建议列表
            showSuggestions: false, // 是否显示建议
            suggestionsLoading: false, // 建议加载状态
            searchTime: null,  // 添加搜索用时字段
        }
    },
    computed: {
        // 计算总页数
        totalPages() {
            return Math.ceil(this.totalResults / this.pageSize) || 1
        },
        // 生成页码导航
        pageNavigation() {
            const pages = []
            const maxVisiblePages = 7  // 最多显示的页码数
            
            if (this.totalPages <= maxVisiblePages) {
                // 如果总页数较少，显示所有页码
                for (let i = 1; i <= this.totalPages; i++) {
                    pages.push(i)
                }
            } else {
                // 总是显示第一页
                pages.push(1)
                
                // 当前页远离首页时显示省略号
                if (this.currentPage > 3) {
                    pages.push('...')
                }
                
                // 当前页附近的页码
                let startPage = Math.max(2, this.currentPage - 1)
                let endPage = Math.min(this.totalPages - 1, this.currentPage + 1)
                
                // 特殊情况处理
                if (this.currentPage <= 3) {
                    endPage = Math.min(5, this.totalPages - 1)
                }
                if (this.currentPage >= this.totalPages - 2) {
                    startPage = Math.max(2, this.totalPages - 4)
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    pages.push(i)
                }
                
                // 当前页远离末页时显示省略号
                if (this.currentPage < this.totalPages - 2) {
                    pages.push('...')
                }
                
                // 总是显示最后一页
                if (this.totalPages > 1) {
                    pages.push(this.totalPages)
                }
            }
            
            return pages
        },
        formattedAiResponse() {
            if (!this.aiResponse) return "";
            
            // 使用markdown-it渲染
            if (this.md) {
                try {
                    return this.md.render(this.aiResponse);
                } catch (error) {
                    console.error("Markdown渲染错误:", error);
                }
            }
            
            // 回退到marked库
            try {
                return marked.parse(this.aiResponse);
            } catch (error) {
                console.error("Markdown解析错误:", error);
                // 如果解析失败，返回原始文本
                return this.aiResponse.replace(/\n/g, '<br>');
            }
        },
        // 格式化结果数显示
        formattedResultCount() {
            if (this.totalResults >= 300) {
                return "300+";
            }
            return this.totalResults.toString();
        },
    },
    mounted() {
        console.log('Vue app mounted')
        
        // 初始化markdown-it
        this.md = window.markdownit({
            html: true,           // 允许HTML（如果内容安全可信）
            breaks: true,         // 更明确地强制换行转为<br>
            linkify: true,        // 自动识别URL
            typographer: true,    // 添加一些语言特性
            highlight: function(str, lang) {  // 代码高亮
                return '<pre class="code-block"><code>' + str + '</code></pre>';
            }
        });
        
        // 检查暗黑模式偏好
        const savedMode = localStorage.getItem('dark-mode');
        if (savedMode === 'true') {
            this.enableDarkMode();
        }
        
        // 检查AI搜索偏好
        const aiEnabled = localStorage.getItem('ai-search-enabled');
        if (aiEnabled !== null) {
            this.aiSearchEnabled = aiEnabled === 'true';
        }
        
        // 添加点击事件监听
        document.addEventListener('click', (e) => {
            // 如果点击的不是搜索框和建议框
            if (
                this.$refs.searchInput && 
                !this.$refs.searchInput.contains(e.target) && 
                !e.target.closest('.suggestions-container')
            ) {
                this.hideSuggestions();
            }
        });
    },
    methods: {
        async search() {
            if (!this.searchQuery.trim()) return
            
            // 保存当前查询
            this.lastSearchQuery = this.searchQuery;
            
            // 清空之前的结果
            this.loading = true
            this.allResults = []
            this.currentResults = []
            this.searched = false
            this.currentPage = 1
            this.showSuggestions = false; // 隐藏建议
            
            // 如果启用了AI搜索，开始流式响应
            if (this.aiSearchEnabled) {
                this.startAiStream();
            } else {
                // 确保关闭先前的AI响应
                this.closeAiResponse();
            }
            
            try {
                console.log('发送查询:', this.searchQuery)
                const requestData = {
                    query: this.searchQuery,
                    type: this.searchType,
                };
                
                const response = await fetch(this.apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                })

                console.log('响应状态:', response.status, response.statusText)
                
                // 检查响应是否成功
                if (!response.ok) {
                    throw new Error(`HTTP错误: ${response.status}`);
                }
                
                const data = await response.json()
                console.log('后端返回的数据:', data)
                
                // 详细记录结果内容
                if (data.results && data.results.length > 0) {
                    console.log('第一个结果:', data.results[0])
                    console.log('结果类型:', typeof data.results)
                    console.log('结果长度:', data.results.length)
                } else {
                    console.log('没有结果或结果为空数组')
                }

                if (data.error) {
                    console.error('搜索错误:', data.error)
                    this.allResults = []
                    this.totalResults = 0
                } else {
                    // 保存所有结果
                    this.allResults = Array.isArray(data.results) ? data.results : []
                    this.totalResults = data.count || 0
                    console.log(`成功接收结果: ${this.allResults.length} 条`)
                    
                    // 更新当前页
                    this.updatePage(1)
                }
                this.searched = true
                this.searchTime = data.elapsed_time || null

            } catch (error) {
                console.error('搜索出错:', error)
                this.allResults = []
                this.currentResults = []
                this.totalResults = 0
                this.searched = true
            } finally {
                this.loading = false
            }
        },
        
        // 更新当前页显示的结果
        updatePage(pageNum) {
            this.currentPage = pageNum
            const startIndex = (pageNum - 1) * this.pageSize
            const endIndex = Math.min(startIndex + this.pageSize, this.allResults.length)
            this.currentResults = this.allResults.slice(startIndex, endIndex)
            
            // 滚动到页面顶部
            window.scrollTo(0, 0)
        },
        
        // 页码导航
        goToPage(page) {
            if (typeof page === 'number' && page >= 1 && page <= this.totalPages) {
                this.updatePage(page)
            }
        },
        
        clearSearch() {
            this.searchQuery = ''
            this.allResults = []
            this.currentResults = []
            this.totalResults = 0
            this.currentPage = 1
            this.searched = false
            this.$refs.searchInput.focus()
        },
        
        // Add dark mode toggle method
        toggleDarkMode() {
            this.isDarkMode = !this.isDarkMode;
            if (this.isDarkMode) {
                this.enableDarkMode();
            } else {
                this.disableDarkMode();
            }
            // Save preference
            localStorage.setItem('dark-mode', this.isDarkMode);
        },
        
        enableDarkMode() {
            document.body.classList.add('dark-mode');
            this.isDarkMode = true;
        },
        
        disableDarkMode() {
            document.body.classList.remove('dark-mode');
            this.isDarkMode = false;
        },
        
        startAiStream() {
            // 重置和显示 AI 响应区域
            this.aiResponse = "";
            this.showAiResponse = true;
            this.isAiLoading = true;
            
            // 关闭之前的流
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            
            try {
                console.log("正在连接AI流式API...");
                const query = encodeURIComponent(this.searchQuery.trim());
                const endpoint = `/api/ai-stream?query=${query}`;
                console.log("使用端点:", endpoint);
                
                // 使用新的端点创建EventSource
                this.eventSource = new EventSource(endpoint);
                
                // 连接建立时
                this.eventSource.onopen = (event) => {
                    console.log("SSE连接已建立:", event);
                };
                
                // 接收消息 - 修改数据处理方式
                this.eventSource.onmessage = (event) => {
                    console.log("收到SSE消息:", event.data);
                    this.isAiLoading = false;
                    
                    if (event.data === "[DONE]") {
                        console.log("AI回答完成");
                        if (this.eventSource) {
                            this.eventSource.close();
                            this.eventSource = null;
                        }
                        return;
                    }
                    
                    // 关键修复：将服务器发送的\\n转换回实际的换行符
                    let newText = event.data.replace(/\\n/g, '\n');
                    
                    // 添加到累积的响应中
                    this.aiResponse += newText;
                    
                    // 尝试解析累积的回应，看是否需要格式修复
                    let formattedResponse = this.aiResponse;
                    
                    // 修复常见的Markdown格式问题
                    formattedResponse = formattedResponse
                        // 确保标题前有空行
                        .replace(/([^\n])###/g, "$1\n\n###")
                        // 确保列表项有适当的换行
                        .replace(/([^\n])(- |• |\* )/g, "$1\n$2");
                    
                    // 更新修复后的响应
                    this.aiResponse = formattedResponse;
                    
                    // 每次收到新数据后重新渲染整个内容
                    this.$nextTick(() => {
                        if (this.md) {
                            const contentElement = document.querySelector('.ai-answer');
                            if (contentElement) {
                                try {
                                    // 渲染完整的累积响应为HTML
                                    contentElement.innerHTML = this.md.render(this.aiResponse);
                                    
                                    // 诊断日志
                                    console.log("渲染后的响应:", this.aiResponse);
                                } catch (error) {
                                    console.error("渲染错误:", error);
                                    // 应急措施：直接显示文本与换行
                                    contentElement.innerText = this.aiResponse;
                                }
                            }
                        }
                        
                        // 滚动到底部
                        const contentContainer = document.querySelector('.ai-response-content');
                        if (contentContainer) {
                            contentContainer.scrollTop = contentContainer.scrollHeight;
                        }
                    });
                };
                
                // 错误处理
                this.eventSource.onerror = (event) => {
                    console.error("SSE连接错误:", event);
                    this.isAiLoading = false;
                    if (this.aiResponse === "") {
                        this.aiResponse = "抱歉，生成回答时出错。请稍后再试。";
                    }
                    if (this.eventSource) {
                        this.eventSource.close();
                        this.eventSource = null;
                    }
                };
            } catch (error) {
                console.error("创建SSE连接时出错:", error);
                this.isAiLoading = false;
                this.aiResponse = "无法连接到AI服务。";
            }
        },
        
        closeAiResponse() {
            this.showAiResponse = false;
            if (this.eventSource) {
                this.eventSource.close();
            }
        },
        
        toggleAiSearch() {
            const previousState = this.aiSearchEnabled;
            this.aiSearchEnabled = !this.aiSearchEnabled;
            
            // 保存用户偏好
            localStorage.setItem('ai-search-enabled', this.aiSearchEnabled);
            
            // 如果已经有搜索结果，且开启了AI功能，则触发AI查询
            if (this.searched && !previousState && this.aiSearchEnabled && this.searchQuery.trim()) {
                // 只启动AI流，不重新搜索
                this.startAiStream();
            }
            
            // 如果关闭了AI功能，则隐藏当前AI回答
            if (!this.aiSearchEnabled) {
                this.closeAiResponse();
            }
        },
        
        // 显示查询建议
        async showQuerySuggestions() {
            // 如果没有上次的查询，不显示建议
            if (!this.lastSearchQuery) return;
            
            this.suggestionsLoading = true;
            this.showSuggestions = true;
            
            try {
                const response = await fetch(
                    `http://${window.location.hostname}:${window.location.port}/api/query-suggestions?query=${encodeURIComponent(this.lastSearchQuery)}`
                );
                
                if (response.ok) {
                    const data = await response.json();
                    this.suggestions = data.suggestions;
                } else {
                    console.error('获取查询建议失败:', response.statusText);
                    this.suggestions = [];
                }
            } catch (error) {
                console.error('获取查询建议错误:', error);
                this.suggestions = [];
            } finally {
                this.suggestionsLoading = false;
            }
        },
        
        // 选择建议
        selectSuggestion(suggestion) {
            this.searchQuery = suggestion;
            this.showSuggestions = false;
            this.search(); // 立即执行搜索
        },
        
        // 隐藏建议的方法
        hideSuggestions() {
            this.showSuggestions = false;
        },
        
        // 高亮显示关键词
        highlightKeywords(content, keywords) {
            if (!content || !keywords || keywords.length === 0) return content;
            
            let highlightedContent = content;
            // 为每个关键词添加高亮样式
            keywords.forEach(keyword => {
                if (!keyword) return;
                
                // 创建不区分大小写的正则表达式
                const regex = new RegExp(`(${keyword})`, 'gi');
                highlightedContent = highlightedContent.replace(
                    regex, 
                    '<span class="highlight-keyword">$1</span>'
                );
            });
            
            return highlightedContent + '...';
        }
    },
}).mount('#app')

window.addEventListener('error', function(event) {
    console.error('Global error:', event.error)
}) 