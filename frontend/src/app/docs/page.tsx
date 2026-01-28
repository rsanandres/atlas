'use client';

import { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Box, Container, CircularProgress, Typography, IconButton, List, ListItem, ListItemButton, ListItemText } from '@mui/material';
import { ArrowLeft, FileText } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface TocItem {
    id: string;
    text: string;
    level: number;
}

export default function DocumentationPage() {
    const [markdown, setMarkdown] = useState('');
    const [loading, setLoading] = useState(true);
    const [activeSection, setActiveSection] = useState('');
    const router = useRouter();

    useEffect(() => {
        fetch('/technical_documentation.md')
            .then(res => res.text())
            .then(text => {
                setMarkdown(text);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load documentation:', err);
                setLoading(false);
            });
    }, []);

    // Extract table of contents from markdown
    const tableOfContents = useMemo(() => {
        if (!markdown) return [];

        const headingRegex = /^(#{1,3})\s+(.+)$/gm;
        const toc: TocItem[] = [];
        let match;

        while ((match = headingRegex.exec(markdown)) !== null) {
            const level = match[1].length;
            const text = match[2].trim();

            // Skip if it's just a number (like "1. System Overview")
            if (level === 2) {
                // Create slug from text
                const id = text
                    .toLowerCase()
                    .replace(/[^\w\s-]/g, '')
                    .replace(/\s+/g, '-');

                toc.push({ id, text, level });
            }
        }

        return toc;
    }, [markdown]);

    // Handle scroll to section
    const scrollToSection = (id: string) => {
        setActiveSection(id);
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    // Add IDs to headings for navigation
    const processedMarkdown = useMemo(() => {
        if (!markdown) return '';

        return markdown.replace(/^## (.+)$/gm, (match, text) => {
            const id = text
                .toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-');
            return `<h2 id="${id}">${text}</h2>`;
        });
    }, [markdown]);

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default' }}>
            {/* Fixed Header */}
            <Box sx={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bgcolor: 'background.paper',
                borderBottom: 1,
                borderColor: 'divider',
                zIndex: 1000,
                px: 3,
                py: 2
            }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <IconButton onClick={() => router.push('/')} size="small">
                        <ArrowLeft size={20} />
                    </IconButton>
                    <FileText size={20} />
                    <Typography variant="h6" fontWeight="bold">
                        Technical Documentation
                    </Typography>
                </Box>
            </Box>

            {/* Content Area (below fixed header) */}
            <Box sx={{ display: 'flex', flex: 1, mt: '64px' }}>
                {/* Fixed Table of Contents Sidebar */}
                <Box
                    sx={{
                        width: 280,
                        flexShrink: 0,
                        borderRight: 1,
                        borderColor: 'divider',
                        bgcolor: 'background.paper',
                        position: 'fixed',
                        top: 64,
                        left: 0,
                        bottom: 0,
                        overflowY: 'auto',
                        display: { xs: 'none', md: 'block' },
                        // Custom scrollbar styling
                        '&::-webkit-scrollbar': {
                            width: '8px',
                        },
                        '&::-webkit-scrollbar-track': {
                            bgcolor: 'transparent',
                        },
                        '&::-webkit-scrollbar-thumb': {
                            bgcolor: 'divider',
                            borderRadius: '4px',
                            '&:hover': {
                                bgcolor: 'text.disabled',
                            },
                        },
                    }}
                >
                    <Box sx={{ p: 2 }}>
                        <Typography variant="caption" fontWeight="bold" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                            TABLE OF CONTENTS
                        </Typography>
                        <List dense disablePadding>
                            {tableOfContents.map((item, index) => (
                                <ListItem key={index} disablePadding>
                                    <ListItemButton
                                        onClick={() => scrollToSection(item.id)}
                                        selected={activeSection === item.id}
                                        sx={{
                                            borderRadius: 1,
                                            mb: 0.5,
                                            '&.Mui-selected': {
                                                bgcolor: 'primary.main',
                                                color: 'primary.contrastText',
                                                '&:hover': {
                                                    bgcolor: 'primary.dark',
                                                }
                                            }
                                        }}
                                    >
                                        <ListItemText
                                            primary={item.text}
                                            primaryTypographyProps={{
                                                variant: 'body2',
                                                fontSize: '0.875rem'
                                            }}
                                        />
                                    </ListItemButton>
                                </ListItem>
                            ))}
                        </List>
                    </Box>
                </Box>

                {/* Main Content (with left margin to account for fixed sidebar) */}
                <Box sx={{
                    flex: 1,
                    ml: { xs: 0, md: '280px' },
                    overflowY: 'auto',
                    height: 'calc(100vh - 64px)'
                }}>
                    <Container maxWidth="lg" sx={{ py: 4 }}>
                        <Box
                            sx={{
                                bgcolor: 'background.paper',
                                borderRadius: 2,
                                p: 4,
                                boxShadow: 1,
                                '& img': {
                                    maxWidth: '100%',
                                    height: 'auto',
                                    borderRadius: 1,
                                    my: 2,
                                },
                                '& h1': {
                                    fontSize: '2.5rem',
                                    fontWeight: 700,
                                    mt: 4,
                                    mb: 2,
                                    borderBottom: '2px solid',
                                    borderColor: 'divider',
                                    pb: 1,
                                },
                                '& h2': {
                                    fontSize: '2rem',
                                    fontWeight: 600,
                                    mt: 3,
                                    mb: 2,
                                    scrollMarginTop: '80px',
                                },
                                '& h3': {
                                    fontSize: '1.5rem',
                                    fontWeight: 600,
                                    mt: 2,
                                    mb: 1.5,
                                },
                                '& h4': {
                                    fontSize: '1.25rem',
                                    fontWeight: 600,
                                    mt: 2,
                                    mb: 1,
                                },
                                '& p': {
                                    mb: 2,
                                    lineHeight: 1.7,
                                },
                                '& code': {
                                    bgcolor: 'action.hover',
                                    px: 1,
                                    py: 0.5,
                                    borderRadius: 0.5,
                                    fontFamily: 'monospace',
                                    fontSize: '0.9em',
                                },
                                '& pre': {
                                    bgcolor: '#1e1e1e',
                                    color: '#d4d4d4',
                                    p: 2,
                                    borderRadius: 1,
                                    overflow: 'auto',
                                    my: 2,
                                    '& code': {
                                        bgcolor: 'transparent',
                                        p: 0,
                                        color: 'inherit',
                                    },
                                },
                                '& table': {
                                    width: '100%',
                                    borderCollapse: 'collapse',
                                    my: 2,
                                },
                                '& th': {
                                    bgcolor: 'action.hover',
                                    p: 1.5,
                                    textAlign: 'left',
                                    fontWeight: 600,
                                    borderBottom: '2px solid',
                                    borderColor: 'divider',
                                },
                                '& td': {
                                    p: 1.5,
                                    borderBottom: '1px solid',
                                    borderColor: 'divider',
                                },
                                '& ul, & ol': {
                                    pl: 3,
                                    mb: 2,
                                },
                                '& li': {
                                    mb: 0.5,
                                },
                                '& blockquote': {
                                    borderLeft: '4px solid',
                                    borderColor: 'primary.main',
                                    pl: 2,
                                    ml: 0,
                                    fontStyle: 'italic',
                                    color: 'text.secondary',
                                },
                                '& a': {
                                    color: 'primary.main',
                                    textDecoration: 'none',
                                    '&:hover': {
                                        textDecoration: 'underline',
                                    },
                                },
                                '& hr': {
                                    my: 3,
                                    border: 'none',
                                    borderTop: '1px solid',
                                    borderColor: 'divider',
                                },
                            }}
                        >
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeRaw]}
                            >
                                {processedMarkdown}
                            </ReactMarkdown>
                        </Box>
                    </Container>
                </Box>
            </Box>
        </Box>
    );
}
