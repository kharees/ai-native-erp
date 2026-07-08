from typing import List, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.finance_core import (
    Account, AccountGroup, JournalEntryLine, JournalVoucher, AccountCategory, JournalStatus
)
from app.schemas.finance_reports import (
    TrialBalanceReport, TrialBalanceLine,
    ProfitAndLossReport, PLCategoryLine,
    BalanceSheetReport, BSCategoryLine,
    CashFlowReport, CashFlowCategoryLine
)

class FinanceReportsService:
    
    async def generate_trial_balance(
        self, db: AsyncSession, tenant_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> TrialBalanceReport:
        # Complex query to sum all posted lines per account
        stmt = (
            select(
                Account.account_code,
                Account.name,
                AccountGroup.category,
                func.sum(JournalEntryLine.debit).label('total_debit'),
                func.sum(JournalEntryLine.credit).label('total_credit')
            )
            .join(AccountGroup, Account.group_id == AccountGroup.id)
            .join(JournalEntryLine, JournalEntryLine.account_id == Account.id)
            .join(JournalVoucher, JournalEntryLine.voucher_id == JournalVoucher.id)
            .where(
                Account.tenant_id == tenant_id,
                JournalVoucher.status == JournalStatus.POSTED
            )
        )
        
        if start_date:
            stmt = stmt.where(func.date(JournalVoucher.entry_date) >= start_date)
        if end_date:
            stmt = stmt.where(func.date(JournalVoucher.entry_date) <= end_date)
            
        stmt = stmt.group_by(Account.account_code, Account.name, AccountGroup.category)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        lines = []
        tot_debit = Decimal("0.00")
        tot_credit = Decimal("0.00")
        
        for row in rows:
            debit = Decimal(str(row.total_debit or "0.00"))
            credit = Decimal(str(row.total_credit or "0.00"))
            lines.append(
                TrialBalanceLine(
                    account_code=row.account_code,
                    account_name=row.name,
                    account_type=row.category.value,
                    period_debit=debit,
                    period_credit=credit,
                    closing_debit=debit if debit > credit else Decimal("0.00"),
                    closing_credit=credit if credit > debit else Decimal("0.00")
                )
            )
            tot_debit += debit
            tot_credit += credit
            
        return TrialBalanceReport(
            tenant_id=str(tenant_id),
            start_date=start_date,
            end_date=end_date,
            lines=lines,
            total_debit=tot_debit,
            total_credit=tot_credit
        )
        
    async def generate_profit_and_loss(
        self, db: AsyncSession, tenant_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> ProfitAndLossReport:
        tb = await self.generate_trial_balance(db, tenant_id, start_date, end_date)
        
        revenue_lines = []
        cogs_lines = []
        expense_lines = []
        
        total_revenue = Decimal("0.00")
        total_cogs = Decimal("0.00")
        total_expense = Decimal("0.00")
        
        for line in tb.lines:
            # Net for income/expense is usually credit - debit for income, debit - credit for expense
            if line.account_type == "income":
                net = line.period_credit - line.period_debit
                total_revenue += net
                revenue_lines.append(PLCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
            elif line.account_type == "expense":
                net = line.period_debit - line.period_credit
                # Simple heuristic: if account contains 'COGS' or 'Cost of Goods', put in COGS
                if "cogs" in line.account_name.lower() or "cost of goods" in line.account_name.lower():
                    total_cogs += net
                    cogs_lines.append(PLCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
                else:
                    total_expense += net
                    expense_lines.append(PLCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
                    
        gross_profit = total_revenue - total_cogs
        net_profit = gross_profit - total_expense
        
        return ProfitAndLossReport(
            tenant_id=str(tenant_id),
            start_date=start_date,
            end_date=end_date,
            revenue=revenue_lines,
            cogs=cogs_lines,
            gross_profit=gross_profit,
            operating_expenses=expense_lines,
            operating_profit=net_profit,
            net_profit=net_profit
        )

    async def generate_balance_sheet(
        self, db: AsyncSession, tenant_id: UUID, as_of_date: date
    ) -> BalanceSheetReport:
        tb = await self.generate_trial_balance(db, tenant_id, end_date=as_of_date)
        pl = await self.generate_profit_and_loss(db, tenant_id, end_date=as_of_date)
        
        asset_lines = []
        liability_lines = []
        equity_lines = []
        
        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")
        total_equity = Decimal("0.00")
        
        for line in tb.lines:
            if line.account_type == "asset":
                net = line.period_debit - line.period_credit
                total_assets += net
                asset_lines.append(BSCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
            elif line.account_type == "liability":
                net = line.period_credit - line.period_debit
                total_liabilities += net
                liability_lines.append(BSCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
            elif line.account_type == "equity":
                net = line.period_credit - line.period_debit
                total_equity += net
                equity_lines.append(BSCategoryLine(category_name=line.account_name, amount=net, accounts=[]))
                
        # Add Retained Earnings (Net Profit from P&L)
        if pl.net_profit != Decimal("0.00"):
            total_equity += pl.net_profit
            equity_lines.append(BSCategoryLine(category_name="Retained Earnings", amount=pl.net_profit, accounts=[]))
            
        return BalanceSheetReport(
            tenant_id=str(tenant_id),
            as_of_date=as_of_date,
            assets=asset_lines,
            total_assets=total_assets,
            liabilities=liability_lines,
            total_liabilities=total_liabilities,
            equity=equity_lines,
            total_equity=total_equity
        )

    async def generate_cash_flow(
        self, db: AsyncSession, tenant_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CashFlowReport:
        # Simplified indirect method approximation using P&L net profit
        pl = await self.generate_profit_and_loss(db, tenant_id, start_date, end_date)
        net_income = pl.net_profit
        
        # In a real system, you'd calculate changes in working capital
        op_activities = [CashFlowCategoryLine(description="Net Income", amount=net_income)]
        net_op_cash = net_income
        
        inv_activities = []
        net_inv_cash = Decimal("0.00")
        
        fin_activities = []
        net_fin_cash = Decimal("0.00")
        
        net_increase = net_op_cash + net_inv_cash + net_fin_cash
        
        return CashFlowReport(
            tenant_id=str(tenant_id),
            start_date=start_date,
            end_date=end_date,
            operating_activities=op_activities,
            net_operating_cash=net_op_cash,
            investing_activities=inv_activities,
            net_investing_cash=net_inv_cash,
            financing_activities=fin_activities,
            net_financing_cash=net_fin_cash,
            net_cash_increase=net_increase,
            opening_cash_balance=Decimal("0.00"), # Mock
            closing_cash_balance=net_increase # Mock
        )

    async def generate_dashboard_summary(
        self, db: AsyncSession, tenant_id: UUID, as_of_date: date
    ) -> dict:
        pl = await self.generate_profit_and_loss(db, tenant_id, end_date=as_of_date)
        
        revenue = sum(item.amount for item in pl.revenue)
        net_profit = pl.net_profit
        margin = (net_profit / revenue * 100) if revenue else Decimal("0.00")
        
        return {
            "revenue": float(revenue),
            "netProfit": float(net_profit),
            "operatingMargin": float(round(margin, 2)),
            "cashPosition": 0.00,
            "arOutstanding": 0.00,
            "apOutstanding": 0.00
        }

finance_reports_service = FinanceReportsService()
