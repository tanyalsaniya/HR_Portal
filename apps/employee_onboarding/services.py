# apps/employee_onboarding/services.py
import os
import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.template import Template, Context
from weasyprint import HTML
from .models import EmployeeDocument, LetterTemplate

DEFAULT_TEMPLATES = [
    {
        'name': 'OFFER_LETTER',
        'title': 'Default Offer Letter Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Offer Letter</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: #555;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #000;
        }
        .title {
            font-weight: bold;
            font-size: 14pt;
            margin-bottom: 25px;
            text-align: center;
        }
        .date {
            margin-bottom: 15px;
        }
        .address {
            margin-bottom: 15px;
        }
        .salutation {
            margin-bottom: 15px;
        }
        .intro {
            margin-bottom: 15px;
            text-align: justify;
        }
        .list-item {
            margin-bottom: 15px;
            display: table;
            width: 100%;
            page-break-inside: avoid;
        }
        .list-number {
            display: table-cell;
            width: 25px;
            font-weight: bold;
            vertical-align: top;
        }
        .list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .nested-list-item {
            margin-top: 8px;
            margin-bottom: 8px;
            display: table;
            width: 100%;
        }
        .nested-list-number {
            display: table-cell;
            width: 25px;
            font-weight: bold;
            vertical-align: top;
        }
        .nested-list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .double-nested-list-item {
            margin-top: 6px;
            margin-bottom: 6px;
            display: table;
            width: 100%;
        }
        .double-nested-list-number {
            display: table-cell;
            width: 20px;
            font-weight: bold;
            vertical-align: top;
        }
        .double-nested-list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .signature-row {
            margin-top: 30px;
            display: table;
            width: 100%;
            page-break-inside: avoid;
        }
        .signature-col {
            display: table-cell;
            vertical-align: bottom;
            font-size: 9.5pt;
        }
        .salary-table {
            width: 55%;
            margin: 20px auto 30px auto;
            border-collapse: collapse;
            font-size: 10pt;
        }
        .salary-table td {
            padding: 6px 12px;
            border: 1px solid #000;
        }
    </style>
</head>
<body>
    <div class="title">Offer Letter</div>
    
    <div class="date">Date: {{ date }}</div>
    <div class="address">{{ address }}</div>
    <div class="salutation">Dear {{ name }},</div>
    
    <div class="intro">
        We are pleased to offer you a position of <strong>{{ designation }}</strong> at <strong>{{ company_name }}</strong>. (Hereinafter to be referred as a “Company”), commencing from <strong>{{ joining_date }}</strong> or another mutually agreed upon date and you will report to Mr. Prince Parbhakar, The Project Manager at {{ company_name }}.
    </div>
    
    <div class="intro">
        Please note that your employment with the company shall be governed by the policies, rules and regulations of the company as specifically mentioned herein by way of references and in force or as amended or altered time to time/ duly notified. The terms and conditions mentioned below:
    </div>

    <div class="list-item">
        <div class="list-number">1.</div>
        <div class="list-content">
            <strong>Remuneration:</strong> The Company is pleased to offer you INR {{ ctc }} CTC per month. Your compensation is confidential and should not be disclosed or discussed with any other employee of the organization. It may be adjusted periodically in accordance with the company’s prevailing employee remuneration guidelines.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">2.</div>
        <div class="list-content">
            <strong>Probation:</strong> You will be on probation for 3 months from the date of joining the company. The company retains the right to terminate the employment of any employee immediately for just cause, without prior notice or compensation in lieu of notice. If the termination is for reasons other than just cause, the company will comply with the legal requirement to provide the minimum notice period stipulated by law.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">3.</div>
        <div class="list-content">
            <strong>General Policy:</strong> This role required a full time commitment, Monday to Friday, with a total of 9 hours per day, incorporating a 45 minutes lunch break from 1:30PM to 2:15PM.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">4.</div>
        <div class="list-content">
            <strong>Leave Policy:</strong>
            <div class="nested-list-item">
                <div class="nested-list-number">A.</div>
                <div class="nested-list-content">During the probation period, employees are not eligible for paid leave.</div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">B.</div>
                <div class="nested-list-content">As a regular employee, you may take up to 1 full day leave and 1 half day or 2 short leaves per month, subject to prior approval and adherence to company policies.</div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">C.</div>
                <div class="nested-list-content">
                    <strong>Sandwich:-</strong>
                    <div class="double-nested-list-item">
                        <div class="double-nested-list-number">1.</div>
                        <div class="double-nested-list-content">If an employee takes leave on Friday and Monday then it will be counted as a sandwich leave and there is no relaxation in this situation.</div>
                    </div>
                    <div class="double-nested-list-item">
                        <div class="double-nested-list-number">2.</div>
                        <div class="double-nested-list-content">If the employee leaves on Friday, Saturday, Sunday OR Saturday, Sunday, Monday then it will also be considered as a sandwich leave but we will give exemption once in every 3 months.</div>
                    </div>
                </div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">D.</div>
                <div class="nested-list-content">Carried forward leaves are limited to one financial year and Six leaves encashment will be allowed at the end of the year.</div>
            </div>
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">5.</div>
        <div class="list-content">
            <strong>Non-Disclosure of Information:</strong> As a part of your employment, you agree to keep all company information confidential, including business strategies, and financial data. Unauthorized disclosure may lead to disciplinary action, including termination and potential legal consequences.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">6.</div>
        <div class="list-content">
            <strong>Proprietary Information and Inventions Agreement:</strong> As a condition of your employment, you will be required to sign the Company’s Proprietary Information and Inventions Agreement.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">7.</div>
        <div class="list-content">
            <strong>Tax Matters:</strong>
            <div class="nested-list-item">
                <div class="nested-list-number">&bull;</div>
                <div class="nested-list-content">
                    <strong>Tax Advice:</strong> You are encouraged to obtain your own tax advice regarding your compensation from the Company. You agree that the Company does not have a duty to design its compensation policies in a manner that minimizes your tax liabilities, and you will not make any claim against the Company or its Board of Directors related to tax liabilities arising from your compensation.
                </div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">&bull;</div>
                <div class="nested-list-content">
                    <strong>Interpretation, Amendment and Enforcement:</strong> This letter agreement supersedes and replaces any prior agreements, representations or understandings (whether written, oral, implied or otherwise) between you and the Company and constitutes the complete agreement between you and the Company regarding the subject matter set forth herein. This letter agreement may not be amended or modified, except by an express written agreement signed by both you and a duly authorized officer of the Company. You may indicate your agreement with these terms and accept this offer by signing and dating this agreement or before (<strong>{{ joining_date }}</strong>). Upon your acceptance of this employment offer, <strong>{{ company_name }}</strong> will provide you with the necessary paperwork and instructions.
                </div>
            </div>
        </div>
    </div>
    
    <div style="margin-top: 25px; text-align: left; page-break-inside: avoid;">
        <p>Sincerely,</p>
    </div>
    
    <div style="margin-top: 35px; text-align: left; page-break-inside: avoid;">
        <div>……………………………………</div>
        <div style="margin-top: 4px;">Applicant (Sign)</div>
    </div>

    <div class="signature-row" style="margin-top: 50px;">
        <div class="signature-col" style="width: 33%; text-align: left;">
            <div style="display: inline-block; text-align: left;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">Company Representative (Sign)</div>
                <div style="margin-top: 4px;">Date – {{ date }}</div>
            </div>
        </div>
        <div class="signature-col" style="width: 34%; text-align: center;">
            <div style="display: inline-block; text-align: center;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">(CTO)</div>
            </div>
        </div>
        <div class="signature-col" style="width: 33%; text-align: right;">
            <div style="display: inline-block; text-align: center;">
                <div>………………………………….</div>
                <div style="margin-top: 4px;">(HR Department)</div>
            </div>
        </div>
    </div>

    <div style="page-break-before: always;"></div>
    
    <div style="font-weight: bold; font-size: 14pt; margin-top: 15px; margin-bottom: 25px; text-align: center;">SALARY BREAKUP</div>
    
    <table class="salary-table">
        <tbody>
            <tr>
                <td style="width: 65%;">CTC</td>
                <td style="width: 35%;">{{ ctc }}</td>
            </tr>
            <tr>
                <td>ESI - EMPLOYER SHARE</td>
                <td>{{ esi_employer }}</td>
            </tr>
            <tr>
                <td>PF - EMPLOYER SHARE</td>
                <td>{{ pf_employer }}</td>
            </tr>
            <tr>
                <td>GROSS</td>
                <td>{{ gross_salary }}</td>
            </tr>
            <tr>
                <td>PF - EMPLOYEE SHARE</td>
                <td>{{ pf_employee }}</td>
            </tr>
            <tr>
                <td>ESI - EMPLOYEE SHARE</td>
                <td>{{ esi_employee }}</td>
            </tr>
            <tr>
                <td>LWF</td>
                <td>{{ lwf }}</td>
            </tr>
            <tr>
                <td>PROFESSIONAL TAX</td>
                <td>{{ professional_tax }}</td>
            </tr>
            <tr>
                <td>IN-HAND</td>
                <td>{{ in_hand }}</td>
            </tr>
        </tbody>
    </table>

    <div style="margin-top: 35px; text-align: left; page-break-inside: avoid;">
        <div>……………………………………</div>
        <div style="margin-top: 4px;">Applicant (Sign)</div>
    </div>

    <div class="signature-row" style="margin-top: 50px;">
        <div class="signature-col" style="width: 33%; text-align: left;">
            <div style="display: inline-block; text-align: left;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">Company Representative (Sign)</div>
                <div style="margin-top: 4px;">Date – {{ date }}</div>
            </div>
        </div>
        <div class="signature-col" style="width: 34%; text-align: center;">
            <div style="display: inline-block; text-align: center;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">(CTO)</div>
            </div>
        </div>
        <div class="signature-col" style="width: 33%; text-align: right;">
            <div style="display: inline-block; text-align: center;">
                <div>………………………………….</div>
                <div style="margin-top: 4px;">(HR Department)</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    },
    {
        'name': 'APPOINTMENT_LETTER',
        'title': 'Default Appointment Letter Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Appointment Letter</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: #555;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #000;
        }
        .title {
            font-weight: bold;
            font-size: 14pt;
            margin-bottom: 25px;
            text-align: center;
        }
        .date {
            margin-bottom: 15px;
        }
        .address {
            margin-bottom: 15px;
        }
        .salutation {
            margin-bottom: 15px;
        }
        .intro {
            margin-bottom: 15px;
            text-align: justify;
        }
        .list-item {
            margin-bottom: 15px;
            display: table;
            width: 100%;
            page-break-inside: avoid;
        }
        .list-number {
            display: table-cell;
            width: 25px;
            font-weight: bold;
            vertical-align: top;
        }
        .list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .nested-list-item {
            margin-top: 8px;
            margin-bottom: 8px;
            display: table;
            width: 100%;
        }
        .nested-list-number {
            display: table-cell;
            width: 25px;
            font-weight: bold;
            vertical-align: top;
        }
        .nested-list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .double-nested-list-item {
            margin-top: 6px;
            margin-bottom: 6px;
            display: table;
            width: 100%;
        }
        .double-nested-list-number {
            display: table-cell;
            width: 20px;
            font-weight: bold;
            vertical-align: top;
        }
        .double-nested-list-content {
            display: table-cell;
            vertical-align: top;
            text-align: justify;
        }
        .signature-row {
            margin-top: 30px;
            display: table;
            width: 100%;
            page-break-inside: avoid;
        }
        .signature-col {
            display: table-cell;
            vertical-align: bottom;
            font-size: 9.5pt;
        }
        .salary-table {
            width: 55%;
            margin: 20px auto 30px auto;
            border-collapse: collapse;
            font-size: 10pt;
        }
        .salary-table td {
            padding: 6px 12px;
            border: 1px solid #000;
        }
    </style>
</head>
<body>
    <div class="title">Appointment Letter</div>
    
    <div class="date">Date: {{ date }}</div>
    <div class="address">{{ address }}</div>
    <div class="salutation">Dear {{ name }},</div>
    
    <div class="intro">
        We are pleased to offer you a position of <strong>{{ designation }}</strong> at <strong>{{ company_name }}</strong>. (Hereinafter to be referred as a “Company”), commencing from <strong>{{ joining_date }}</strong> or another mutually agreed upon date and you will report to Mr. Prince Parbhakar, The Project Manager at {{ company_name }}.
    </div>
    
    <div class="intro">
        Please note that your employment with the company shall be governed by the policies, rules and regulations of the company as specifically mentioned herein by way of references and in force or as amended or altered time to time/ duly notified. The terms and conditions mentioned below:
    </div>

    <div class="list-item">
        <div class="list-number">1.</div>
        <div class="list-content">
            <strong>Remuneration:</strong> The Company is pleased to offer you INR {{ ctc }} CTC per month. Your compensation is confidential and should not be disclosed or discussed with any other employee of the organization. It may be adjusted periodically in accordance with the company’s prevailing employee remuneration guidelines.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">2.</div>
        <div class="list-content">
            <strong>Probation:</strong> You will be on probation for 3 months from the date of joining the company. The company retains the right to terminate the employment of any employee immediately for just cause, without prior notice or compensation in lieu of notice. If the termination is for reasons other than just cause, the company will comply with the legal requirement to provide the minimum notice period stipulated by law.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">3.</div>
        <div class="list-content">
            <strong>General Policy:</strong> This role required a full time commitment, Monday to Friday, with a total of 9 hours per day, incorporating a 45 minutes lunch break from 1:30PM to 2:15PM.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">4.</div>
        <div class="list-content">
            <strong>Leave Policy:</strong>
            <div class="nested-list-item">
                <div class="nested-list-number">A.</div>
                <div class="nested-list-content">During the probation period, employees are not eligible for paid leave.</div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">B.</div>
                <div class="nested-list-content">As a regular employee, you may take up to 1 full day leave and 1 half day or 2 short leaves per month, subject to prior approval and adherence to company policies.</div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">C.</div>
                <div class="nested-list-content">
                    <strong>Sandwich:-</strong>
                    <div class="double-nested-list-item">
                        <div class="double-nested-list-number">1.</div>
                        <div class="double-nested-list-content">If an employee takes leave on Friday and Monday then it will be counted as a sandwich leave and there is no relaxation in this situation.</div>
                    </div>
                    <div class="double-nested-list-item">
                        <div class="double-nested-list-number">2.</div>
                        <div class="double-nested-list-content">If the employee leaves on Friday, Saturday, Sunday OR Saturday, Sunday, Monday then it will also be considered as a sandwich leave but we will give exemption once in every 3 months.</div>
                    </div>
                </div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">D.</div>
                <div class="nested-list-content">Carried forward leaves are limited to one financial year and Six leaves encashment will be allowed at the end of the year.</div>
            </div>
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">5.</div>
        <div class="list-content">
            <strong>Non-Disclosure of Information:</strong> As a part of your employment, you agree to keep all company information confidential, including business strategies, and financial data. Unauthorized disclosure may lead to disciplinary action, including termination and potential legal consequences.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">6.</div>
        <div class="list-content">
            <strong>Proprietary Information and Inventions Agreement:</strong> As a condition of your employment, you will be required to sign the Company’s Proprietary Information and Inventions Agreement.
        </div>
    </div>
    
    <div class="list-item">
        <div class="list-number">7.</div>
        <div class="list-content">
            <strong>Tax Matters:</strong>
            <div class="nested-list-item">
                <div class="nested-list-number">&bull;</div>
                <div class="nested-list-content">
                    <strong>Tax Advice:</strong> You are encouraged to obtain your own tax advice regarding your compensation from the Company. You agree that the Company does not have a duty to design its compensation policies in a manner that minimizes your tax liabilities, and you will not make any claim against the Company or its Board of Directors related to tax liabilities arising from your compensation.
                </div>
            </div>
            <div class="nested-list-item">
                <div class="nested-list-number">&bull;</div>
                <div class="nested-list-content">
                    <strong>Interpretation, Amendment and Enforcement:</strong> This letter agreement supersedes and replaces any prior agreements, representations or understandings (whether written, oral, implied or otherwise) between you and the Company and constitutes the complete agreement between you and the Company regarding the subject matter set forth herein. This letter agreement may not be amended or modified, except by an express written agreement signed by both you and a duly authorized officer of the Company. You may indicate your agreement with these terms and accept this offer by signing and dating this agreement or before (<strong>{{ joining_date }}</strong>). Upon your acceptance of this employment offer, <strong>{{ company_name }}</strong> will provide you with the necessary paperwork and instructions.
                </div>
            </div>
        </div>
    </div>
    
    <div style="margin-top: 25px; text-align: left; page-break-inside: avoid;">
        <p>Sincerely,</p>
    </div>
    
    <div style="margin-top: 35px; text-align: left; page-break-inside: avoid;">
        <div>……………………………………</div>
        <div style="margin-top: 4px;">Applicant (Sign)</div>
    </div>

    <div class="signature-row" style="margin-top: 50px;">
        <div class="signature-col" style="width: 33%; text-align: left;">
            <div style="display: inline-block; text-align: left;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">Company Representative (Sign)</div>
                <div style="margin-top: 4px;">Date – {{ date }}</div>
            </div>
        </div>
        <div class="signature-col" style="width: 34%; text-align: center;">
            <div style="display: inline-block; text-align: center;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">(CTO)</div>
            </div>
        </div>
        <div class="signature-col" style="width: 33%; text-align: right;">
            <div style="display: inline-block; text-align: center;">
                <div>………………………………….</div>
                <div style="margin-top: 4px;">(HR Department)</div>
            </div>
        </div>
    </div>

    <div style="page-break-before: always;"></div>
    
    <div style="font-weight: bold; font-size: 14pt; margin-top: 15px; margin-bottom: 25px; text-align: center;">SALARY BREAKUP</div>
    
    <table class="salary-table">
        <tbody>
            <tr>
                <td style="width: 65%;">CTC</td>
                <td style="width: 35%;">{{ ctc }}</td>
            </tr>
            <tr>
                <td>ESI - EMPLOYER SHARE</td>
                <td>{{ esi_employer }}</td>
            </tr>
            <tr>
                <td>PF - EMPLOYER SHARE</td>
                <td>{{ pf_employer }}</td>
            </tr>
            <tr>
                <td>GROSS</td>
                <td>{{ gross_salary }}</td>
            </tr>
            <tr>
                <td>PF - EMPLOYEE SHARE</td>
                <td>{{ pf_employee }}</td>
            </tr>
            <tr>
                <td>ESI - EMPLOYEE SHARE</td>
                <td>{{ esi_employee }}</td>
            </tr>
            <tr>
                <td>LWF</td>
                <td>{{ lwf }}</td>
            </tr>
            <tr>
                <td>PROFESSIONAL TAX</td>
                <td>{{ professional_tax }}</td>
            </tr>
            <tr>
                <td>IN-HAND</td>
                <td>{{ in_hand }}</td>
            </tr>
        </tbody>
    </table>

    <div style="margin-top: 35px; text-align: left; page-break-inside: avoid;">
        <div>……………………………………</div>
        <div style="margin-top: 4px;">Applicant (Sign)</div>
    </div>

    <div class="signature-row" style="margin-top: 50px;">
        <div class="signature-col" style="width: 33%; text-align: left;">
            <div style="display: inline-block; text-align: left;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">Company Representative (Sign)</div>
                <div style="margin-top: 4px;">Date – {{ date }}</div>
            </div>
        </div>
        <div class="signature-col" style="width: 34%; text-align: center;">
            <div style="display: inline-block; text-align: center;">
                <div>……………………………………</div>
                <div style="margin-top: 4px;">(CTO)</div>
            </div>
        </div>
        <div class="signature-col" style="width: 33%; text-align: right;">
            <div style="display: inline-block; text-align: center;">
                <div>………………………………….</div>
                <div style="margin-top: 4px;">(HR Department)</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    },
    {
        'name': 'BOND_LETTER',
        'title': 'Default Employment Bond Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Employment Bond Agreement</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: 'Times New Roman', Times, serif;
                font-size: 9pt;
                color: #000;
            }
        }
        body {
            font-family: 'Times New Roman', Times, serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #000;
            background-color: #fff;
        }
        .title {
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            margin: 20px 0 30px 0;
            text-transform: uppercase;
            text-decoration: underline;
        }
        .content {
            margin-bottom: 30px;
            text-align: justify;
        }
        .content p {
            margin-bottom: 15px;
            text-indent: 0px;
        }
        .signature-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
            page-break-inside: avoid;
        }
        .signature-table td {
            padding: 8px 0;
            font-size: 11pt;
            vertical-align: bottom;
        }
    </style>
</head>
<body>
    <div class="title">Employment Bond Letter</div>
    
    <div class="content">
        <p>THIS AGREEMENT made as of the <strong>{{ date }}</strong>, between <strong>{{ company_name }}</strong> and <strong>{{ employee_name }}</strong> and having its principal place of business at {{ company_address }}. WHEREAS the Employer desires to obtain the benefit of the services of the Employee, and the Employee desires to render such services on the terms and conditions set forth.</p>
        
        <p>IN CONSIDERATION of the promises and other good and valuable consideration (the sufficiency and receipt of which are hereby acknowledged) the parties agree as follows:-</p>
        
        <p><strong>1. Employment:</strong><br>
        The Employee agrees that he will at all times faithfully, industriously, and to the best of his skill, ability, experience and talents, perform all of the duties required of his position. In carrying out these duties and responsibilities, the Employee shall comply with all Employer policies, procedures, rules and regulations, both written and oral, as are announced by the Employer from time to time. It is also understood and agreed to by the Employee that his assignment, duties and responsibilities and reporting arrangements may be changed by the Employer in its sole discretion without causing termination of this agreement.</p>
        
        <p><strong>2. Position Title:</strong><br>
        As a {{ designation }} the Employee is required to perform the duties and undertake responsibilities in a professional manner which may be assigned by the employer. This Agreement shall be defined as, the employee will not leave the position at least {{ bond_period }} months. In case they broke this agreement and left in between without notice period or any serious issues they have to give back two months’ salary to the company.</p>
        
        <p><strong>3. Compensation:</strong><br>
        (a) As full compensation for all services provided the employee shall be paid at the given rate. Such payments shall be subject to such normal statutory deductions by the Employer.<br>
        (b) The salary mentioned in your offer letter.<br>
        (c) All reasonable expenses arising out of employment shall be reimbursed assuming the same have been authorized prior to being incurred and with the provision of appropriate receipts.</p>
        
        <p><strong>4. Probation Period:</strong><br>
        It is understood and agreed that the {{ probation_period }} months of employment shall constitute a probationary period during which period the Employer may, in its absolute discretion, terminate the Employee's employment, for any reason without notice or cause. If your services are found to be satisfactory during the probationary period, you will be confirmed in the present position and thereafter your services can be terminated on {{ notice_period }} days of notice on either side.</p>
        
        <p><strong>5. Performance Reviews:</strong><br>
        The Employee will be provided with a written performance appraisal at least once per year and said appraisal will be reviewed by the manager at which time all aspects of the assessment can be fully discussed.</p>
        
        <p><strong>6. Termination and Resignation:</strong><br>
        (a) The Employee shall not terminate this agreement and his employment during the time of the bond period. Employees have to give two months' prior written notice to the Employer and have to pay 2 months' salary to the company if the Employee leaves the company before the bond period.<br>
        (b) The Employer may terminate this Agreement and the Employee’s employment at any time, without notice or payment in lieu of notice, for sufficient cause.<br>
        (c) If the employee will not serve given Notice and leave the organization in that case company will not provide any Experience letter and employee has to give back two months’ salary to company.<br>
        (d) The Government Exams, Female marriage, planning to go abroad for further future in that case the company will relieve the employee after receiving official documents.<br>
        (e) The employee agrees to return any property of the company at the time of termination.</p>
        
        <p><strong>7. Non- Competition:</strong><br>
        (1) It is further acknowledged and agreed that following termination of the employee’s employment with {{ company_name }} for any reason the employee shall not hire or attempt to hire any current employees of {{ company_name }}.<br>
        (2) It is further acknowledged and agreed that following termination of the employee’s employment with {{ company_name }} for any reason the employee shall not solicit business from current clients or existing clients, in that case the company will take legal action against them.</p>
        
        <p><strong>8. Pay and Incentive Policy:</strong><br>
        Pay shall be given by the medium of the bank on the 10th of every month. Incentives are subjected to the performance of the employee.</p>
        
        <p><strong>9. Holiday/ Vacation/ Leave:</strong><br>
        The list of holidays will be displayed and the information shall be conveyed to the employees. The employees are given Eighteen leaves per year i.e. one full day leave per month and one half day leave or two short days leaves per month. If any employee is not taking any leave in a month that leave is going to be added in the next month and any employee can take a maximum of two carry forwarded leaves in a month otherwise there will be salary deduction. If any employee takes leave before or after week offs and holidays then it will be counted as a sandwich.</p>
        
        <p><strong>10. Entire Agreement:</strong><br>
        This agreement contains the entire agreement between the parties, superseding in all respects any and all prior oral or written agreements or understandings pertaining to the employment of the Employee by the Employer and shall be amended or modified only by written instrument signed by both of the parties here to.</p>
        
        <p><strong>11. IN WITNESS WHEREOF:</strong><br>
        The Employer has caused this agreement to be executed by its duly authorized officers and the Employee has set his hand as of the date first above written.</p>
    </div>
    
    <div style="margin-top: 45px; page-break-inside: avoid;">
        <p>SIGNED, SEALED AND DELIVERED in the presence of:</p>
        <table class="signature-table">
            <tr>
                <td style="width: 45%;">[Name of employee] _______________________</td>
                <td style="width: 55%;">{{ employee_name }}</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Signature of Employee] __________________</td>
                <td style="width: 55%;">___________________________________________</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Name of Employer Rep] __________________</td>
                <td style="width: 55%;">{{ signatory_name }}</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Signature of Employer Rep] ______________</td>
                <td style="width: 55%;">___________________________________________</td>
            </tr>
        </table>
    </div>
</body>
</html>"""
    }
]

def sync_db_templates():
    from .models import LetterTemplate
    for t in DEFAULT_TEMPLATES:
        if not LetterTemplate.objects.filter(name=t['name']).exists():
            LetterTemplate.objects.create(**t)

def render_letter_to_html(employee, doc_type, custom_context=None):
    """
    Renders the letter template (from DB or fallback HTML file) to a string using custom context.
    """
    sync_db_templates()
    context = get_letter_context(employee, custom_context)
    
    template_name_map = {
        'OFFER_LETTER': 'onboarding/pdf_offer_letter.html',
        'APPOINTMENT_LETTER': 'onboarding/pdf_appointment_letter.html',
        'BOND_LETTER': 'onboarding/pdf_bond_letter.html',
    }
    template_name = template_name_map.get(doc_type, 'onboarding/pdf_offer_letter.html')
    
    # Check if a database template exists
    template_obj = LetterTemplate.objects.filter(name=doc_type).first()
    if template_obj:
        html_string = Template(template_obj.html_content).render(Context(context))
    else:
        # Render HTML template to string
        html_string = render_to_string(template_name, context)
        
    return html_string

def generate_document_pdf(employee, doc_type, template_name, context, user=None):
    """
    Renders an HTML template with context, generates a PDF using WeasyPrint,
    saves the PDF to the media folder, and logs it as an EmployeeDocument.
    """
    sync_db_templates()
    # Check if a database template exists
    template_obj = LetterTemplate.objects.filter(name=doc_type).first()
    if template_obj:
        html_string = Template(template_obj.html_content).render(Context(context))
    else:
        # Render HTML template to string
        html_string = render_to_string(template_name, context)
    
    # Generate PDF bytes via WeasyPrint
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    # Prepare File content
    filename = f"{doc_type.lower()}_{employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    content_file = ContentFile(pdf_bytes, name=filename)
    
    # Create EmployeeDocument record
    doc = EmployeeDocument.objects.create(
        bitrix_user_id=employee.id,
        doc_type=doc_type,
        file=content_file,
        uploaded_by=user
    )
    return doc


import re
from django.utils.safestring import mark_safe, SafeData

def sanitize_html_context(val):
    if callable(val):
        return val
    elif isinstance(val, dict):
        return {k: sanitize_html_context(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_html_context(v) for v in val]
    elif isinstance(val, tuple):
        return tuple(sanitize_html_context(v) for v in val)
    elif isinstance(val, str) and not isinstance(val, SafeData):
        formatted = val.replace('\n', '<br>')
        # Convert ordinals like 1st, 2nd, 3rd, 22nd to superscript HTML
        def replace_ordinal(match):
            return f"{match.group(1)}<sup>{match.group(2)}</sup>"
        formatted = re.sub(r'\b(\d+)(st|nd|rd|th|ST|ND|RD|TH)\b', replace_ordinal, formatted)
        return mark_safe(formatted)
    return val


def get_letter_context(employee, custom_context=None):
    salary_struct = employee.salary_structures.order_by('-effective_from').first()
    
    custom_context = custom_context or {}
    
    # Format today's date
    date_str = custom_context.get('date', datetime.date.today().strftime('%d %B %Y'))
    
    # Create customizable employee dict
    custom_emp = {
        'first_name': custom_context.get('first_name', employee.first_name),
        'last_name': custom_context.get('last_name', employee.last_name),
        'emp_id': custom_context.get('emp_id', employee.emp_id),
        'designation': custom_context.get('designation', employee.designation),
        'joining_date': custom_context.get('joining_date', employee.joining_date.strftime('%Y-%m-%d') if employee.joining_date else ''),
        'notice_period_days': custom_context.get('notice_period_days', employee.notice_period_days),
        'bond_period_months': custom_context.get('bond_period_months', employee.bond_period_months),
        'address_line1': custom_context.get('address_line1', employee.address_line1),
        'city': custom_context.get('city', employee.city),
        'state': custom_context.get('state', employee.state),
        'get_state_display': employee.get_state_display(),
    }
    
    # Support direct variable fallback in template like name, address, designation, date
    context = {
        'employee': custom_emp,
        'today': datetime.date.today(),
        'date': date_str,
        'bond_date': date_str,
        'employee_name': f"{custom_emp['first_name']} {custom_emp['last_name']}",
        'name': f"{custom_emp['first_name']} {custom_emp['last_name']}",
        'address': f"{custom_emp['address_line1']}, {custom_emp['city']}",
        'employee_address': f"{custom_emp['address_line1']}, {custom_emp['city']}",
        'designation': custom_emp['designation'],
        'joining_date': custom_emp['joining_date'],
        'company_name': custom_context.get('company_name', getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd.')),
        'company_address': custom_context.get('company_address', getattr(settings, 'COMPANY_ADDRESS', 'Plot No D-254, Fourth Floor, Phase 8A, Industrial Area, Mohali')),
        'signatory_name': custom_context.get('signatory_name', getattr(settings, 'LETTER_SIGNATORY_NAME', 'Head of HR Operations')),
        'signatory_designation': custom_context.get('signatory_designation', getattr(settings, 'LETTER_SIGNATORY_DESIGNATION', 'Authorized Signatory')),
    }
    
    # Populate salary details safely
    basic = custom_context.get('basic', str(getattr(salary_struct, 'basic_salary', getattr(salary_struct, 'basic', '0.00'))) if salary_struct else '0.00')
    hra = custom_context.get('hra', str(getattr(salary_struct, 'hra', '0.00')) if salary_struct else '0.00')
    conveyance = custom_context.get('conveyance', str(getattr(salary_struct, 'conveyance', '0.00')) if salary_struct else '0.00')
    medical = custom_context.get('medical', str(getattr(salary_struct, 'medical_allowance', '0.00')) if salary_struct else '0.00')
    special = custom_context.get('special', str(getattr(salary_struct, 'special_allowance', '0.00')) if salary_struct else '0.00')
    monthly_bonus = custom_context.get('monthly_bonus', str(getattr(salary_struct, 'monthly_bonus', '0.00')) if salary_struct else '0.00')
    
    pf = custom_context.get('pf', str(getattr(salary_struct, 'pf_employee', getattr(salary_struct, 'pf_contribution', '0.00'))) if salary_struct else '0.00')
    pt = custom_context.get('professional_tax', str(getattr(salary_struct, 'professional_tax', '200.00')) if salary_struct else '200.00')
    tds = custom_context.get('tds', str(getattr(salary_struct, 'tds', '0.00')) if salary_struct else '0.00')
    
    gross_salary = custom_context.get('gross_salary', str(getattr(salary_struct, 'gross_salary', '0.00')) if salary_struct else '0.00')
    total_deductions = custom_context.get('total_deductions', str(getattr(salary_struct, 'total_deductions', '0.00')) if salary_struct else '0.00')
    net_salary = custom_context.get('net_salary', str(getattr(salary_struct, 'net_salary', '0.00')) if salary_struct else '0.00')
    
    # Extra breakup fields requested
    ctc = custom_context.get('ctc', str(getattr(salary_struct, 'ctc', gross_salary)) if salary_struct else '0.00')
    esi_employer = custom_context.get('esi_employer', str(getattr(salary_struct, 'esi_employer', '0.00')) if salary_struct else '0.00')
    pf_employer = custom_context.get('pf_employer', str(getattr(salary_struct, 'pf_employer', '0.00')) if salary_struct else '0.00')
    pf_employee = custom_context.get('pf_employee', pf)
    esi_employee = custom_context.get('esi_employee', str(getattr(salary_struct, 'esi_employee', getattr(salary_struct, 'esi', '0.00'))) if salary_struct else '0.00')
    lwf = custom_context.get('lwf', str(getattr(salary_struct, 'lwf', getattr(salary_struct, 'labour_welfare_fund', '0.00'))) if salary_struct else '0.00')
    in_hand = custom_context.get('in_hand', str(getattr(salary_struct, 'in_hand_salary', net_salary)) if salary_struct else '0.00')
    
    context.update({
        'salary': salary_struct if salary_struct else True,
        'basic': basic,
        'hra': hra,
        'conveyance': conveyance,
        'medical': medical,
        'special': special,
        'monthly_bonus': monthly_bonus,
        'pf': pf,
        'professional_tax': pt,
        'tds': tds,
        'gross_salary': gross_salary,
        'total_deductions': total_deductions,
        'net_salary': net_salary,
        
        'ctc': ctc,
        'esi_employer': esi_employer,
        'pf_employer': pf_employer,
        'pf_employee': pf_employee,
        'esi_employee': esi_employee,
        'lwf': lwf,
        'in_hand': in_hand,
        
        'bond_period': custom_emp['bond_period_months'],
        'probation_period': '3',
        'notice_period': custom_emp['notice_period_days'],
        'penalty_salary': 'two months’ salary',
        
        'other_allowances': getattr(salary_struct, 'other_allowances', []),
        'other_deductions': [
            {'label': 'ESI', 'amount': getattr(salary_struct, 'esi', 0)},
            {'label': 'Labour Welfare Fund', 'amount': getattr(salary_struct, 'labour_welfare_fund', 0)},
            {'label': 'Other Deductions', 'amount': getattr(salary_struct, 'other_deductions', 0)},
        ] if salary_struct else [],
    })
    
    return sanitize_html_context(context)

def generate_offer_letter(employee, user=None, custom_context=None):
    context = get_letter_context(employee, custom_context)
    return generate_document_pdf(
        employee=employee,
        doc_type='OFFER_LETTER',
        template_name='onboarding/pdf_offer_letter.html',
        context=context,
        user=user
    )

def generate_appointment_letter(employee, user=None, custom_context=None):
    context = get_letter_context(employee, custom_context)
    return generate_document_pdf(
        employee=employee,
        doc_type='APPOINTMENT_LETTER',
        template_name='onboarding/pdf_appointment_letter.html',
        context=context,
        user=user
    )

def generate_bond_letter(employee, user=None, custom_context=None):
    bond_period = employee.bond_period_months
    if custom_context and 'bond_period_months' in custom_context:
        bond_period = int(custom_context['bond_period_months'] or 0)
        
    if not bond_period:
        raise ValueError("Employee does not have a bond period defined.")
        
    context = get_letter_context(employee, custom_context)
    context['bond_period'] = bond_period
    return generate_document_pdf(
        employee=employee,
        doc_type='BOND_LETTER',
        template_name='onboarding/pdf_bond_letter.html',
        context=context,
        user=user
    )
