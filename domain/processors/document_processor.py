"""
文档处理服务 - 负责文档加载、分割和预处理
职责：文档格式转换、文本分割、内容过滤
"""
import os
from typing import List, Tuple
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentProcessor:
    """文档处理服务"""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        max_chunk_length: int = 250
    ):
        """
        初始化文档处理器
        
        Args:
            chunk_size: 文本分块大小
            chunk_overlap: 文本块重叠大小
            max_chunk_length: 单个文本块最大长度（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_length = max_chunk_length
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " "]
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Document]: 加载的文档列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件类型
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        filename = os.path.basename(file_path)
        
        # PDF 文件
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            print(f"  加载 PDF: {len(docs)} 页")
            return docs
        
        # 文本文件
        elif file_path.endswith(('.txt', '.md')):
            docs = self._load_text_file(file_path)
            print(f"  加载文本文件: {len(docs)} 个文档")
            return docs
        
        else:
            raise ValueError(f"不支持的文件类型: {filename}")
    
    def _load_text_file(self, file_path: str) -> List[Document]:
        """
        尝试多种编码加载文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Document]: 加载的文档
            
        Raises:
            ValueError: 所有编码都失败
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
        
        for encoding in encodings:
            try:
                loader = TextLoader(file_path, encoding=encoding)
                docs = loader.load()
                print(f"  使用 {encoding} 编码加载成功")
                return docs
            except Exception:
                continue
        
        raise ValueError(f"无法加载文件，尝试了所有编码: {encodings}")
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        分割文档为文本块
        
        Args:
            documents: 原始文档列表
            
        Returns:
            List[Document]: 分割后的文本块列表
        """
        splits = self.text_splitter.split_documents(documents)
        print(f"  分割为 {len(splits)} 个文本块")
        return splits
    
    def filter_and_truncate(self, documents: List[Document]) -> List[Document]:
        """
        过滤和截断过长的文本块
        
        Args:
            documents: 文档列表
            
        Returns:
            List[Document]: 处理后的文档列表
        """
        filtered = []
        for doc in documents:
            content = doc.page_content
            if len(content) > self.max_chunk_length:
                doc.page_content = content[:self.max_chunk_length] + "..."
            filtered.append(doc)
        
        print(f"  过滤后保留 {len(filtered)} 个文本块")
        return filtered
    
    def add_metadata(
        self,
        documents: List[Document],
        file_id: str,
        filename: str,
        agent_name: str
    ) -> List[Document]:
        """
        为文档添加元数据
        
        Args:
            documents: 文档列表
            file_id: 文件 ID
            filename: 文件名
            agent_name: 智能体名称
            
        Returns:
            List[Document]: 添加元数据后的文档列表
        """
        for doc in documents:
            doc.metadata.update({
                'file_id': file_id,
                'filename': filename,
                'agent_name': agent_name
            })
        return documents
    
    def process_file(
        self,
        file_path: str,
        file_id: str,
        filename: str,
        agent_name: str
    ) -> Tuple[List[Document], dict]:
        """
        完整的文档处理流程
        
        Args:
            file_path: 文件路径
            file_id: 文件 ID
            filename: 文件名
            agent_name: 智能体名称
            
        Returns:
            Tuple[List[Document], dict]: (处理后的文档列表, 处理统计信息)
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件处理错误
        """
        print(f"📄 处理文件: {filename}")
        
        # 1. 加载文档
        docs = self.load_document(file_path)
        
        # 2. 分割文档
        splits = self.split_documents(docs)
        
        # 3. 过滤和截断
        filtered = self.filter_and_truncate(splits)
        
        # 4. 添加元数据
        processed = self.add_metadata(filtered, file_id, filename, agent_name)
        
        # 统计信息
        stats = {
            'original_docs': len(docs),
            'splits': len(splits),
            'filtered': len(filtered),
            'final': len(processed)
        }
        
        return processed, stats


# 全局单例
_document_processor = None


def get_document_processor() -> DocumentProcessor:
    """获取文档处理器单例"""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
