/**
 * Pre-configured realistic transaction CSV datasets for testing changes
 * in FinMitra's 4 engines (stress probabilities, evidence grades, Safe EMI, and repayment scores).
 */

export const SAMPLE_DATASETS = [
  {
    id: 'healthy_kirana',
    title: '🟢 Healthy Kirana Store',
    subtitle: 'High stability, growing sales, low volatility',
    description: '6 months of consistent daily customer UPI collections and steady supplier restocks. Generates low stress probability (~15%), Grade A evidence, and high Safe EMI.',
    defaultContext: {
      borrowerId: 'BORR-KIRANA-01',
      businessName: 'Laxmi Supermarket',
      evaluationDate: '2026-08-31',
      sourceType: 'BANK_STATEMENT',
      householdExpense: 12000,
      balanceBuffer: 15000,
    },
    csvContent: `date,amount,direction,category,narration,counterparty,mode
2026-03-02,4200,CREDIT,BUSINESS_INCOME,QR Payment from Customer,cust_1@upi,UPI
2026-03-05,6500,CREDIT,BUSINESS_INCOME,Weekly Store Settlement,pos_pay@icici,POS
2026-03-10,3200,DEBIT,OPERATING_EXPENSE,Wholesale FMCG Purchase,distrib_fmcg@bank,BANK_TRANSFER
2026-03-15,5100,CREDIT,BUSINESS_INCOME,QR Collection,cust_2@upi,UPI
2026-03-20,7800,CREDIT,BUSINESS_INCOME,Weekend Sales Bulk,cust_3@upi,UPI
2026-03-25,4500,DEBIT,OPERATING_EXPENSE,Inventory Restock,metro_cash@bank,BANK_TRANSFER
2026-04-02,4800,CREDIT,BUSINESS_INCOME,QR Payment from Customer,cust_4@upi,UPI
2026-04-08,8200,CREDIT,BUSINESS_INCOME,Card Settlement POS,pos_pay@icici,POS
2026-04-12,3900,DEBIT,OPERATING_EXPENSE,Wholesale Purchase,distrib_fmcg@bank,BANK_TRANSFER
2026-04-18,6200,CREDIT,BUSINESS_INCOME,UPI Sales,cust_5@upi,UPI
2026-04-26,5500,DEBIT,OPERATING_EXPENSE,Store Utility & Rent,landlord@bank,BANK_TRANSFER
2026-05-03,5900,CREDIT,BUSINESS_INCOME,Customer UPI,cust_6@upi,UPI
2026-05-10,9100,CREDIT,BUSINESS_INCOME,Weekly POS Batch,pos_pay@icici,POS
2026-05-15,4100,DEBIT,OPERATING_EXPENSE,FMCG Supply,distrib_fmcg@bank,BANK_TRANSFER
2026-05-22,6800,CREDIT,BUSINESS_INCOME,QR Payment,cust_7@upi,UPI
2026-06-04,6100,CREDIT,BUSINESS_INCOME,Daily Sales Batch,cust_8@upi,UPI
2026-06-11,9400,CREDIT,BUSINESS_INCOME,POS Card Settlement,pos_pay@icici,POS
2026-06-18,4800,DEBIT,OPERATING_EXPENSE,Inventory Restock,distrib_fmcg@bank,BANK_TRANSFER
2026-06-25,7200,CREDIT,BUSINESS_INCOME,UPI Customer Pay,cust_9@upi,UPI
2026-07-02,6800,CREDIT,BUSINESS_INCOME,QR Pay Batch,cust_10@upi,UPI
2026-07-10,10200,CREDIT,BUSINESS_INCOME,POS Settlement,pos_pay@icici,POS
2026-07-16,5200,DEBIT,OPERATING_EXPENSE,Wholesale Order,distrib_fmcg@bank,BANK_TRANSFER
2026-07-24,7900,CREDIT,BUSINESS_INCOME,UPI Sales,cust_11@upi,UPI
2026-08-03,7400,CREDIT,BUSINESS_INCOME,Store QR Pay,cust_12@upi,UPI
2026-08-12,11000,CREDIT,BUSINESS_INCOME,Weekly POS Batch,pos_pay@icici,POS
2026-08-18,5800,DEBIT,OPERATING_EXPENSE,Monthly Stocking,distrib_fmcg@bank,BANK_TRANSFER
2026-08-27,8500,CREDIT,BUSINESS_INCOME,Customer UPI Pay,cust_13@upi,UPI`,
  },

  {
    id: 'volatile_vendor',
    title: '🟡 High Volatility Vendor',
    subtitle: 'Erratic income, high cash swings',
    description: 'Extreme variance between good weeks and zero-income weeks. Increases the ML Inflow Volatility metric (>45%) and triggers volatility warnings in the Capacity Engine.',
    defaultContext: {
      borrowerId: 'BORR-VENDOR-02',
      businessName: 'Sharma Event Decor',
      evaluationDate: '2026-08-31',
      sourceType: 'UPI',
      householdExpense: 15000,
      balanceBuffer: 3000,
    },
    csvContent: `date,amount,direction,category,narration,counterparty,mode
2026-03-02,28000,CREDIT,BUSINESS_INCOME,Wedding Advance UPI,client_a@upi,UPI
2026-03-08,18000,DEBIT,OPERATING_EXPENSE,Flower & Fabric Purchase,vendor_fl@bank,BANK_TRANSFER
2026-03-28,2000,CREDIT,BUSINESS_INCOME,Small Party Decor,client_b@upi,UPI
2026-04-05,1500,CREDIT,BUSINESS_INCOME,Minor Booking,client_c@upi,UPI
2026-04-12,8000,DEBIT,OPERATING_EXPENSE,Equipment Repair,workshop@bank,BANK_TRANSFER
2026-04-29,1200,CREDIT,BUSINESS_INCOME,Consultation Fee,client_d@upi,UPI
2026-05-04,35000,CREDIT,BUSINESS_INCOME,Mega Event Contract,event_mgmt@bank,BANK_TRANSFER
2026-05-11,22000,DEBIT,OPERATING_EXPENSE,Temporary Labor & Lights,labor_sup@upi,UPI
2026-05-25,3000,CREDIT,BUSINESS_INCOME,Party Setup,client_e@upi,UPI
2026-06-03,2000,CREDIT,BUSINESS_INCOME,Booking Token,client_f@upi,UPI
2026-06-15,6500,DEBIT,OPERATING_EXPENSE,Transport & Fuel,petrol_bunk@upi,UPI
2026-06-28,1500,CREDIT,BUSINESS_INCOME,Stage Rental,client_g@upi,UPI
2026-07-06,42000,CREDIT,BUSINESS_INCOME,Festival Decor Advance,temple_trust@bank,BANK_TRANSFER
2026-07-14,26000,DEBIT,OPERATING_EXPENSE,Material Bulk Order,decor_wholesaler@bank,BANK_TRANSFER
2026-07-30,2500,CREDIT,BUSINESS_INCOME,Balloon Arch,client_h@upi,UPI
2026-08-04,1800,CREDIT,BUSINESS_INCOME,Photo Booth Setup,client_i@upi,UPI
2026-08-16,7000,DEBIT,OPERATING_EXPENSE,Warehouse Rent,warehouse@bank,BANK_TRANSFER
2026-08-28,3100,CREDIT,BUSINESS_INCOME,Birthday Setup,client_j@upi,UPI`,
  },

  {
    id: 'declining_distressed',
    title: '🔴 Declining / Cash-Stressed Shop',
    subtitle: 'Falling revenue, negative cash-flow months',
    description: 'Inflows shrinking steadily month-over-month while expenses remain elevated. Causes the 90-Day Cash-flow Stress Gauge to swing into the Red (>70%) with negative inflow trend reasons.',
    defaultContext: {
      borrowerId: 'BORR-STRESSED-03',
      businessName: 'City Mobile Repair & Accessories',
      evaluationDate: '2026-08-31',
      sourceType: 'BANK_STATEMENT',
      householdExpense: 18000,
      balanceBuffer: 2000,
    },
    csvContent: `date,amount,direction,category,narration,counterparty,mode
2026-03-05,18000,CREDIT,BUSINESS_INCOME,Phone Sales & Service,walkin_cust@upi,UPI
2026-03-12,12000,DEBIT,OPERATING_EXPENSE,Display Screen Stock,spare_parts@bank,BANK_TRANSFER
2026-03-22,16000,CREDIT,BUSINESS_INCOME,Accessories Wholesale,retailer_b@bank,BANK_TRANSFER
2026-03-29,11000,DEBIT,OPERATING_EXPENSE,Store Rent & Electric,landlord@bank,BANK_TRANSFER
2026-04-06,14000,CREDIT,BUSINESS_INCOME,Daily Repair Earnings,walkin_cust@upi,UPI
2026-04-15,13000,DEBIT,OPERATING_EXPENSE,Battery & Tool Parts,spare_parts@bank,BANK_TRANSFER
2026-04-25,11000,CREDIT,BUSINESS_INCOME,Service Revenue,cust_qr@upi,UPI
2026-04-30,11000,DEBIT,OPERATING_EXPENSE,Monthly Shop Rent,landlord@bank,BANK_TRANSFER
2026-05-07,9500,CREDIT,BUSINESS_INCOME,Customer Walkins,cust_pay@upi,UPI
2026-05-18,12500,DEBIT,OPERATING_EXPENSE,Phone Parts Sourcing,delhi_spares@bank,BANK_TRANSFER
2026-05-27,8200,CREDIT,BUSINESS_INCOME,Case & Screen Protector Sales,walkin_cust@upi,UPI
2026-05-31,11000,DEBIT,OPERATING_EXPENSE,Store Rent,landlord@bank,BANK_TRANSFER
2026-06-08,7000,CREDIT,BUSINESS_INCOME,Screen Replacements,cust_qr@upi,UPI
2026-06-19,10500,DEBIT,OPERATING_EXPENSE,Tooling & Consumables,spare_parts@bank,BANK_TRANSFER
2026-06-28,6200,CREDIT,BUSINESS_INCOME,Accessories Sale,walkin_cust@upi,UPI
2026-06-30,11000,DEBIT,OPERATING_EXPENSE,Store Rent,landlord@bank,BANK_TRANSFER
2026-07-07,5200,CREDIT,BUSINESS_INCOME,Phone Servicing,cust_qr@upi,UPI
2026-07-18,9000,DEBIT,OPERATING_EXPENSE,Component Order,delhi_spares@bank,BANK_TRANSFER
2026-07-26,4800,CREDIT,BUSINESS_INCOME,Small Repair Jobs,walkin_cust@upi,UPI
2026-07-31,11000,DEBIT,OPERATING_EXPENSE,Store Rent,landlord@bank,BANK_TRANSFER
2026-08-06,4100,CREDIT,BUSINESS_INCOME,Repair Ticket Settlement,cust_pay@upi,UPI
2026-08-16,8500,DEBIT,OPERATING_EXPENSE,Spare Parts Import,delhi_spares@bank,BANK_TRANSFER
2026-08-25,3600,CREDIT,BUSINESS_INCOME,Cable & Charger Sales,walkin_cust@upi,UPI
2026-08-31,11000,DEBIT,OPERATING_EXPENSE,Store Rent Overdue,landlord@bank,BANK_TRANSFER`,
  },
]
