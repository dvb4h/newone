package javax.jnlp;
import java.io.*;
public interface FileSaveService {
    FileContents saveFileDialog(String pathHint, String[] extensions, InputStream stream, String name) throws IOException;
    FileContents saveAsFileDialog(String pathHint, String[] extensions, FileContents contents) throws IOException;
}
