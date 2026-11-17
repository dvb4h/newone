package javax.jnlp;
import java.awt.print.*;
public interface PrintService {
    PageFormat getDefaultPage();
    PageFormat showPageFormatDialog(PageFormat page);
    boolean print(Pageable document);
    boolean print(Printable painter);
}
