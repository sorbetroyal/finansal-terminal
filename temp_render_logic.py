
    # ACTUAL RENDERING LOOPS (MISSING PREVIOUSLY)
    with tab_portfolio:
        p_syms = sorted(list(p_assets.keys()))
        
        # Debug/Info for user regarding data source state
        # st.caption(f"Veri Kaynağı: {len(p_syms)} varlık bulundu.")
        
        if not p_syms:
            st.markdown("""
            <div style="text-align:center; padding:50px; color:rgba(255,255,255,0.5);">
                <div style="font-size:3rem; margin-bottom:15px;">📭</div>
                <div style="font-size:1.1rem; font-weight:600;">Portföyünüzde varlık bulunmuyor</div>
                <div style="font-size:0.8rem; margin-top:5px;">Veya veriler henüz yüklenmedi.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            for sym in p_syms:
                render_sc_card(sym, is_watched_tab=False)
                
    with tab_watched:
        # Show strategies on assets we don't own
        w_syms = sorted(list(set(asset_strategies.keys()) - set(p_assets.keys())))
        
        if not w_syms:
             st.markdown("""
            <div style="text-align:center; padding:50px; color:rgba(255,255,255,0.5);">
                <div style="font-size:3rem; margin-bottom:15px;">🔍</div>
                <div style="font-size:1.1rem; font-weight:600;">Takip edilen strateji yok</div>
                <div style="font-size:0.8rem; margin-top:5px;">Portföyünüzde olmayan varlıklar için alarm kurduğunuzda burada görünür.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            for sym in w_syms:
                render_sc_card(sym, is_watched_tab=True)
