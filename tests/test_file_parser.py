import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from src.utils.file_parser import FileParser, SlideContent


class TestFileParser:
    @pytest.fixture
    def file_parser(self):
        return FileParser()
    
    def test_supported_formats(self, file_parser):
        assert '.pptx' in file_parser.supported_formats
        assert '.ppt' in file_parser.supported_formats
        assert '.pdf' in file_parser.supported_formats
    
    def test_unsupported_file_format(self, file_parser):
        with pytest.raises(ValueError, match="Unsupported file format"):
            file_parser.parse_file('test.txt')
    
    @patch('src.utils.file_parser.Presentation')
    def test_parse_powerpoint(self, mock_presentation_class, file_parser):
        # Create mock presentation
        mock_presentation = Mock()
        mock_slide = Mock()
        mock_shape = Mock()
        mock_shape.text = "Test slide content"
        mock_shape.has_table = False
        mock_slide.shapes = [mock_shape]
        mock_presentation.slides = [mock_slide]
        mock_presentation_class.return_value = mock_presentation
        
        # Mock image extraction
        with patch.object(file_parser, '_extract_image_from_slide', return_value=b'fake_image'):
            result = file_parser._parse_powerpoint('test.pptx')
        
        assert len(result) == 1
        assert isinstance(result[0], SlideContent)
        assert result[0].slide_number == 1
        assert result[0].text_content == "Test slide content"
        assert result[0].image_content == b'fake_image'
    
    @patch('src.utils.file_parser.PyPDF2.PdfReader')
    @patch('src.utils.file_parser.convert_from_path')
    def test_parse_pdf(self, mock_convert, mock_pdf_reader_class, file_parser):
        # Create mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "PDF page content"
        mock_pdf_reader = Mock()
        mock_pdf_reader.pages = [mock_page]
        mock_pdf_reader_class.return_value = mock_pdf_reader
        
        # Mock image conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]
        
        with patch('src.utils.file_parser.BytesIO') as mock_bytesio:
            mock_buffer = Mock()
            mock_bytesio.return_value = mock_buffer
            mock_buffer.getvalue.return_value = b'fake_pdf_image'
            
            result = file_parser._parse_pdf('test.pdf')
        
        assert len(result) == 1
        assert isinstance(result[0], SlideContent)
        assert result[0].slide_number == 1
        assert result[0].text_content == "PDF page content"
    
    def test_extract_text_from_slide(self, file_parser):
        # Create mock slide with various shape types
        mock_shape1 = Mock()
        mock_shape1.text = "Text content 1"
        mock_shape1.has_table = False
        
        mock_shape2 = Mock()
        mock_shape2.text = "Text content 2"
        mock_shape2.has_table = True
        
        # Mock table
        mock_cell = Mock()
        mock_cell.text = "Table cell content"
        mock_row = Mock()
        mock_row.cells = [mock_cell]
        mock_table = Mock()
        mock_table.rows = [mock_row]
        mock_shape2.table = mock_table
        
        mock_slide = Mock()
        mock_slide.shapes = [mock_shape1, mock_shape2]
        
        result = file_parser._extract_text_from_slide(mock_slide)
        
        assert "Text content 1" in result
        assert "Text content 2" in result
        assert "Table cell content" in result
    
    @patch('os.path.getsize')
    @patch('os.path.basename')
    @patch('src.utils.file_parser.Presentation')
    def test_extract_metadata_pptx(self, mock_presentation_class, mock_basename, mock_getsize, file_parser):
        mock_basename.return_value = 'test.pptx'
        mock_getsize.return_value = 1024000
        
        # Create mock presentation with metadata
        mock_presentation = Mock()
        mock_presentation.slides = [Mock(), Mock()]  # 2 slides
        mock_core_properties = Mock()
        mock_core_properties.title = "Test Presentation"
        mock_core_properties.author = "Test Author"
        mock_presentation.core_properties = mock_core_properties
        mock_presentation_class.return_value = mock_presentation
        
        metadata = file_parser.extract_metadata('test.pptx')
        
        assert metadata['file_name'] == 'test.pptx'
        assert metadata['file_size'] == 1024000
        assert metadata['file_type'] == '.pptx'
        assert metadata['slide_count'] == 2
        assert metadata['title'] == "Test Presentation"
        assert metadata['author'] == "Test Author"
    
    @patch('os.path.getsize')
    @patch('os.path.basename')
    @patch('src.utils.file_parser.PyPDF2.PdfReader')
    def test_extract_metadata_pdf(self, mock_pdf_reader_class, mock_basename, mock_getsize, file_parser):
        mock_basename.return_value = 'test.pdf'
        mock_getsize.return_value = 2048000
        
        # Create mock PDF reader with metadata
        mock_pdf_reader = Mock()
        mock_pdf_reader.pages = [Mock(), Mock(), Mock()]  # 3 pages
        mock_pdf_reader.metadata = {
            '/Title': 'Test PDF',
            '/Author': 'PDF Author'
        }
        mock_pdf_reader_class.return_value = mock_pdf_reader
        
        metadata = file_parser.extract_metadata('test.pdf')
        
        assert metadata['file_name'] == 'test.pdf'
        assert metadata['file_size'] == 2048000
        assert metadata['file_type'] == '.pdf'
        assert metadata['page_count'] == 3
        assert metadata['title'] == 'Test PDF'
        assert metadata['author'] == 'PDF Author'
    
    def test_slide_content_initialization(self):
        slide = SlideContent(1, "Test content", b'image_data')
        
        assert slide.slide_number == 1
        assert slide.text_content == "Test content"
        assert slide.image_content == b'image_data'
        assert slide.image_base64 is not None
        
        # Test without image
        slide_no_image = SlideContent(2, "Test content 2", None)
        assert slide_no_image.image_content is None
        assert slide_no_image.image_base64 is None


if __name__ == '__main__':
    pytest.main([__file__])