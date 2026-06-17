import sys
try:
    from weasyprint import HTML
    print("WeasyPrint imported successfully.")
    html = HTML(string="<h1>Test</h1>")
    
    # Try PDF
    pdf_bytes = html.write_pdf()
    print(f"PDF generated successfully: {len(pdf_bytes)} bytes")
    
    # Try PNG
    try:
        png_bytes = html.write_png()
        print(f"PNG generated successfully: {len(png_bytes)} bytes")
    except Exception as png_err:
        print(f"PNG generation failed: {png_err}")
except Exception as e:
    print(f"WeasyPrint import or test failed: {e}")
