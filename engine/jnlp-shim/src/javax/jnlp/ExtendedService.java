package javax.jnlp;
import java.io.*;
public interface ExtendedService {
    FileContents openFile(File file) throws IOException;
    FileContents[] openFiles(File[] files) throws IOException;
}
