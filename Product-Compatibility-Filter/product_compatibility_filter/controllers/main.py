import json
import logging

from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute
from datetime import datetime
from werkzeug.urls import url_decode, url_encode, url_parse
from odoo import fields, http, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.tools import lazy
from werkzeug.exceptions import Forbidden, NotFound


class WebsiteSaleCompatibility(WebsiteSale):
    def _get_search_options(
        self, category=None, attrib_values=None, pricelist=None, min_price=0.0, max_price=0.0, conversion_rate=1, classification=None, prod_id=None, specs_values=None, compat_parts=None, **post
    ):
        results = super(WebsiteSaleCompatibility, self)._get_search_options(category, attrib_values, pricelist, min_price, max_price, conversion_rate)
        results.update(classification=str(classification.id) if classification else None)
        results.update(prod_id=str(prod_id) if prod_id else None)
        results.update(specs_values=specs_values if specs_values else None)
        results.update(compat_parts=compat_parts if compat_parts else None)
        return results
    
    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, attrib=None, order=None, specs=None, variants=None, **post):
        results = super(WebsiteSaleCompatibility, self)._shop_get_query_url_kwargs(category, search, min_price, max_price, attrib, order)
        results.update(specs=specs)
        variants = request.httprequest.args.getlist('variants')
        results.update(variants=variants)
        return results
    
    def _prepare_product_values(self, product, category, search, **kwargs):
        results = super(WebsiteSaleCompatibility, self)._prepare_product_values(product, category, search, **kwargs)
        results['specs'] = request.httprequest.args.getlist('specs')
        results['variants'] = request.httprequest.args.getlist('variants')
        return results
    
    def _set_selected_id(self, id_param):
        return int(id_param) if (id_param and id_param.isdigit()) else 0

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>''',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>/page/<int:page>''',
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', ppg=False, class_id=None, product_id=None, min_price=0.0, max_price=0.0, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        # PRODUCT COMPATIBILITY
        Classification = request.env['product.classification']
        if not class_id:
            class_id = Classification
        else:
            class_id = Classification.search([('id', '=', int(class_id))])

        product_classification = Classification.search([])
        
        class_id_param = http.request.params.get('class_id')
        product_id_param = http.request.params.get('product_id')
        
        selected_class_id = self._set_selected_id(class_id_param)
        selected_prod_id = self._set_selected_id(product_id_param)
        
        filter_by = request.env['ir.config_parameter'].sudo().get_param('product_compatibility_filter.filter_by')
        filter_by_specs = True if filter_by == 'specifications' else False
        specs_values = []
        specs_value_ids = {}
        variants_values = []
        compat_parts = []
        found_compat = True
        compat_attrs = None
        compat_attrs_all = None
        compat_attrs_prod = None

        # Filter by specifications
        if filter_by_specs:
            specs_list = request.httprequest.args.getlist('specs')
            specs_values = [[int(x) for x in v.split("-")] for v in specs_list if v]
            specs_value_ids = {v[1] for v in specs_values}
            product_search_domains = [('product_classification', '=', int(class_id)), ('is_part', '=', False)]
            SPEC_LINE = request.env['specification.line']
            specs = None
            ids = []
            for value in specs_values:
                if not specs:
                    specs = value[0]
                    ids.append(value[1])
                elif value[0] == specs:
                    ids.append(value[1])
                else:
                    specification_lines = lazy(lambda: SPEC_LINE.search([('product_specification_name_id', '=', specs), ('product_specification_value_id', 'in', ids)]))
                    product_search_domains.append(('product_specification_line', 'in', specification_lines.ids))
                    specs = value[0]
                    ids = [value[1]]
            if specs:
                specification_lines = lazy(lambda: SPEC_LINE.search([('product_specification_name_id', '=', specs), ('product_specification_value_id', 'in', ids)]))
                product_search_domains.append(('product_specification_line', 'in', specification_lines.ids))
            if selected_prod_id > 0: 
                product_search_domains.append(('id', '=', selected_prod_id))
            products_in_class = request.env['product.template'].search(product_search_domains)

            compat_attrs = None
            if selected_prod_id == 0 and selected_class_id > 0:
                compat_attrs = products_in_class.product_specification_line.product_specification_name_id

        # Filter by variants
        else:
            products_in_class = request.env['product.template'].search([('product_classification', '=', int(class_id)), ('is_part', '=', False)])
            variants = request.httprequest.args.getlist('variants')
            variants_values = [int(var) for var in variants]
            if variants:
                # Getting the parts related to this product variant
                if selected_prod_id > 0:
                    compat_list = request.env['product.product'].search([('product_template_attribute_value_ids', '=', variants)])
                    compat_values = request.env['product.product'].search([('compatible_prods', '=', compat_list.ids)])
                    compat_parts = [int(id) for id in compat_values.ids]
                else: 
                    variants_names = {request.env['product.attribute.value'].search([('id', '=', var_id)]).name for var_id in variants_values}
                    compat_list = request.env['product.product'].search([('product_template_attribute_value_ids.name', 'in', list(variants_names))])
                    compat_values = request.env['product.product'].search([('compatible_prods', '=', compat_list.ids)])
                    compat_parts = [int(id) for id in compat_values.ids]
            
                if len(compat_parts) == 0:
                    found_compat = False
        
            if selected_class_id > 0:
                if selected_prod_id > 0:
                    CompatProductAttribute = request.env['product.template.attribute.line']
                    compat_prod = request.env['product.template'].search([('id', '=', selected_prod_id)])
                    compat_attrs_prod = lazy(lambda: CompatProductAttribute.search([('product_tmpl_id', 'in', compat_prod.ids)]))
                else:
                    CompatProductAttribute = request.env['product.attribute']
                    compat_prod = products_in_class
                    compat_attrs_all = lazy(lambda: CompatProductAttribute.search([('product_tmpl_ids', 'in', compat_prod.ids)]))

        # ===============================================================

        website = request.env['website'].get_current_website()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL('/shop', **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post))

        now = datetime.timestamp(datetime.now())
        pricelist = request.env['product.pricelist'].browse(request.session.get('website_sale_current_pl'))
        if not pricelist or request.session.get('website_sale_pricelist_time', 0) < now - 60*60: # test: 1 hour in session
            pricelist = website.get_current_pricelist()
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        request.update_context(pricelist=pricelist.id, partner=request.env.user.partner_id)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, pricelist.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list


        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            pricelist=pricelist,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            classification=class_id,
            prod_id=product_id,
            specs_values=specs_values,
            compat_parts=compat_parts,
            **post
        )

        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search, website)

        # PRODUCT COMPATIBILITY
        if not filter_by_specs and not found_compat:
            search_product = request.env['product.template']
        # ===================

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_search_domain(search, category, attrib_values)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        website_domain = website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        products_prices = lazy(lambda: products._get_sales_prices(pricelist))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
            'product_classification': product_classification,   # !!!!
            'selected_class_id': selected_class_id,
            'selected_prod_id': selected_prod_id,
            'products_in_class': products_in_class,
            'compat_attrs': compat_attrs,
            'specs_values': specs_values,
            'specs_set': specs_value_ids,
            'compat_attrs_all': compat_attrs_all,
            'compat_attrs_prod': compat_attrs_prod,
            'found_compat': found_compat,
            'variants_values': variants_values,
            'filter_by_specs': filter_by_specs,
        }

        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if category:
            values['main_object'] = category

        values.update(self._get_additional_shop_values(values))
        return request.render("website_sale.products", values)
    