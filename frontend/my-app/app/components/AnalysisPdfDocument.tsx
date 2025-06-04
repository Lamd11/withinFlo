'use client';

import React from '@react-pdf/renderer';

const { Document, Page, Text, View, StyleSheet, Font } = React;

// Define default font (optional, but good for consistency and non-Latin characters)
// You might need to host the font file in your public directory
// Font.register({
//   family: 'Roboto',
//   src: '/fonts/Roboto-Regular.ttf', // Example path
// });

// Create styles
const styles = StyleSheet.create({
  page: {
    flexDirection: 'column',
    backgroundColor: '#FFFFFF',
    padding: 30,
    // fontFamily: 'Roboto', // Use registered font
  },
  title: {
    fontSize: 24,
    textAlign: 'center',
    marginBottom: 20,
    fontWeight: 'bold',
  },
  introduction: {
    fontSize: 12,
    marginBottom: 15,
    textAlign: 'justify',
  },
  section: {
    marginBottom: 15,
  },
  sectionHeading: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333333',
  },
  paragraph: {
    fontSize: 11,
    marginBottom: 5,
    textAlign: 'justify',
    lineHeight: 1.4,
  },
  footer: {
    position: 'absolute',
    fontSize: 10,
    bottom: 15,
    left: 30,
    right: 30,
    textAlign: 'center',
    color: 'grey',
  },
});

interface AnalysisData {
  title?: string;
  introduction?: string;
  sections?: Array<{
    heading?: string;
    paragraphs?: string[];
  }>;
  // Add other fields from your actual JSON structure if needed
}

// Export the props interface
export interface AnalysisPdfDocumentProps {
  data: AnalysisData;
}

// Export the AnalysisData interface as well
export type { AnalysisData };

const AnalysisPdfDocument: React.FC<AnalysisPdfDocumentProps> = ({ data }) => {
  const { title = "Analysis Report", introduction = "", sections = [] } = data || {};

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {title && <Text style={styles.title}>{title}</Text>}
        {introduction && <Text style={styles.introduction}>{introduction}</Text>}

        {sections && sections.map((section, index) => (
          <View key={index} style={styles.section}>
            {section.heading && <Text style={styles.sectionHeading}>{section.heading}</Text>}
            {section.paragraphs && section.paragraphs.map((paragraph, pIndex) => (
              <Text key={pIndex} style={styles.paragraph}>
                {paragraph}
              </Text>
            ))}
          </View>
        ))}
        
        <Text style={styles.footer} fixed>
          Generated on: {new Date().toLocaleDateString()}
        </Text>
      </Page>
    </Document>
  );
};

export default AnalysisPdfDocument; 