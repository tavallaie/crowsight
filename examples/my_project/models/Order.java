// my_project/models/Order.java
package models;

import java.util.List;
import java.time.LocalDate;

public class Order extends BaseEntity {
    private String id;
    private List<String> items;
    private double total;
    private LocalDate createdDate;

    public Order(String id, List<String> items, double total) {
        super();
        this.id = id;
        this.items = items;
        this.total = total;
        this.createdDate = LocalDate.now();
    }

    public double calculateTotalWithTax(double taxRate) {
        return total * (1 + taxRate);
    }

    // getters and setters omitted for brevity
}
