package javax.jnlp;
import java.io.*;
public interface JNLPRandomAccessFile extends DataInput, DataOutput {
    void close() throws IOException;
    long length() throws IOException;
    long getFilePointer() throws IOException;
    int read() throws IOException;
    int read(byte[] b, int off, int len) throws IOException;
    int read(byte[] b) throws IOException;
    void seek(long pos) throws IOException;
    void setLength(long newLength) throws IOException;
}
