#!/usr/bin/env python3
"""
Test the updated theme organization
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_theme_import():
    """Test that themes can be imported and created successfully."""
    try:
        from src.ui.theme import create_plot_themes
        print("✅ Theme import successful")
        
        # Test creating themes
        themes = create_plot_themes()
        print(f"✅ Created {len(themes)} plot themes: {list(themes.keys())}")
        
        # Check theme structure
        required_themes = ['photon_plot', 'image_plot']
        for theme_name in required_themes:
            if theme_name in themes:
                print(f"✅ {theme_name} theme created successfully")
            else:
                print(f"❌ Missing {theme_name} theme")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Theme import/creation error: {e}")
        return False

def test_table_viewer_with_themes():
    """Test that TableViewer can use the new themes."""
    try:
        from src.ui.tables import TableViewer
        
        # Create table viewer instance
        table_viewer = TableViewer()
        
        # Check if plot themes are initialized
        if hasattr(table_viewer, 'plot_themes'):
            print("✅ TableViewer has plot_themes attribute")
            print(f"✅ Available themes: {list(table_viewer.plot_themes.keys())}")
            return True
        else:
            print("❌ TableViewer missing plot_themes attribute")
            return False
            
    except Exception as e:
        print(f"❌ TableViewer theme integration error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run theme organization tests."""
    print("🎨 Testing Theme Organization")
    print("=" * 50)
    
    tests = [
        test_theme_import,
        test_table_viewer_with_themes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Theme organization is working correctly.")
        print("\n🎨 Theme Organization Benefits:")
        print("   • Centralized theme management in theme.py")
        print("   • Reusable plot themes across components")
        print("   • Cleaner, more maintainable code")
        print("   • Consistent styling across the application")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()